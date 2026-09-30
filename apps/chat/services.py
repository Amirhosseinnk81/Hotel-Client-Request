"""
Who may see which conversation, and what happens when a message is sent.

Non-CRUD logic lives here rather than in the views, the same rule as
apps/tickets/services.py — and here it matters more than usual, because
"which conversations can this person see" has to give the same answer to
the REST endpoints, the live stream and the WebSocket consumer. Three
copies of that rule would eventually be three different rules, and the
one that drifts is the one that shows a guest somebody else's thread.
"""

from django.db.models import Count, Q

from apps.departments.models import Department

from . import delivery
from .models import Conversation, Message, Participant


def is_staff_user(user) -> bool:
    return bool(user and user.is_authenticated and user.role in ("OPERATOR", "ADMIN"))


def visible_conversations(user):
    """
    Every conversation `user` is allowed to open — the single definition.

    - A guest sees their own threads and nothing else.
    - An operator sees their own department's guest threads (the same
      scoping as tickets) plus any staff thread they are in.
    - An admin has no department, so they see staff threads they are in.
      Guest support belongs to the departments, not to management.
    """
    base = Conversation.objects.select_related("guest", "department")

    if not (user and user.is_authenticated):
        return base.none()

    if user.role == "GUEST":
        return base.filter(kind=Conversation.Kind.GUEST, guest__user=user)

    mine = Q(participants__user=user)
    if user.role == "OPERATOR" and user.department_id:
        mine |= Q(kind=Conversation.Kind.GUEST, department_id=user.department_id)
    return base.filter(mine).distinct()


def guest_conversation(guest, department: Department) -> Conversation:
    """
    The guest's open thread with a department, opened on first use.

    One open thread per guest per department: a guest asking housekeeping
    two things on the same stay is one conversation, not two, or the
    operator answers in a window that the guest has already left.
    """
    conversation = (
        Conversation.objects.filter(
            kind=Conversation.Kind.GUEST, guest=guest, department=department, is_closed=False
        )
        .order_by("-created_at")
        .first()
    )
    if conversation is None:
        conversation = Conversation.objects.create(
            kind=Conversation.Kind.GUEST, guest=guest, department=department
        )
    join(conversation, guest.user)
    return conversation


def start_staff_conversation(creator, users, subject="") -> Conversation:
    """A staff thread. The creator is always in it, whatever they passed."""
    conversation = Conversation.objects.create(
        kind=Conversation.Kind.STAFF,
        subject=subject.strip(),
        department=getattr(creator, "department", None),
    )
    join(conversation, creator)
    for user in users:
        join(conversation, user)
    return conversation


def find_staff_conversation(creator, users):
    """
    An existing staff thread with exactly this set of people and no
    subject — so "message Reza" twice doesn't leave two empty threads.
    """
    wanted = {creator.pk, *[user.pk for user in users]}
    candidates = (
        Conversation.objects.filter(kind=Conversation.Kind.STAFF, subject="", is_closed=False)
        .annotate(people=Count("participants"))
        .filter(people=len(wanted), participants__user=creator)
        .distinct()
    )
    for conversation in candidates:
        if {p.user_id for p in conversation.participants.all()} == wanted:
            return conversation
    return None


def join(conversation, user) -> Participant:
    participant, _ = Participant.objects.get_or_create(conversation=conversation, user=user)
    return participant


def post_message(conversation, sender, body) -> Message:
    """
    Write the message, then try to push it. In that order, always: a
    message that is in the database will be delivered by the stream even
    if the push fails, while a push that happened before the write could
    show the reader something that isn't saved.
    """
    body = (body or "").strip()
    if not body:
        raise ValueError("A chat message cannot be empty.")

    message = Message.objects.create(conversation=conversation, sender=sender, body=body)
    if sender is not None:
        join(conversation, sender)
        # Sending is reading: the sender never sees their own message as unread.
        mark_read(conversation, sender)
    delivery.publish(message)
    return message


def mark_read(conversation, user) -> None:
    from django.utils import timezone

    Participant.objects.filter(conversation=conversation, user=user).update(
        last_read_at=timezone.now()
    )


def unread_count(conversation, user) -> int:
    """
    Messages this person hasn't seen. Their own messages never count,
    and a thread they joined mid-way counts only from when they joined.

    The two cutoffs are deliberately not the same comparison: "read up
    to here" excludes that instant, while "joined at here" includes it —
    everything from the moment you were added is yours to read. That is
    also what keeps the count honest on Windows, where the clock ticks
    about every 15ms and a join followed straight away by a message can
    carry the identical timestamp.
    """
    participant = conversation.participants.filter(user=user).first()
    if participant is None:
        return 0
    if participant.last_read_at:
        unseen = conversation.messages.filter(created_at__gt=participant.last_read_at)
    else:
        unseen = conversation.messages.filter(created_at__gte=participant.joined_at)
    return unseen.exclude(sender=user).count()


def total_unread(user) -> int:
    """For the badge in the header — one number across every thread."""
    return sum(
        unread_count(conversation, user)
        for conversation in visible_conversations(user).prefetch_related("participants")
    )

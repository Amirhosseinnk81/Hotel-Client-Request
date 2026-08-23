import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function GuestTicketsPage() {
  return (
    <main className="mx-auto flex w-full max-w-lg flex-1 flex-col">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">درخواست‌های من</CardTitle>
          <CardDescription>
            درخواست شما با موفقیت ثبت شد. نمایش کامل لیست درخواست‌ها در فاز بعدی
            تکمیل می‌شود.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </main>
  );
}

# Project Context

## Project Name

Hotel Client Request Platform

---

## Vision

Build a scalable hotel guest request management platform that digitizes the process of receiving, routing, processing, tracking, and analyzing guest requests.

The long-term vision includes AI-powered request classification and routing, notifications, analytics, and operational intelligence.

---

## Problem Statement

Hotel guest requests are currently handled through phone calls, manual communication, and disconnected systems.

This can cause:

- Delayed response times
- Misrouting of requests
- Lack of request tracking
- Poor visibility for hotel operators
- Difficulty measuring department performance
- Loss of historical operational data

The platform aims to centralize and digitize this workflow.

---

## MVP Goal

The initial MVP focuses on building a stable and testable request management system without AI.

The MVP must allow:

1. Guests to authenticate.
2. Guests to submit requests.
3. Guests to view their own requests.
4. Requests to be assigned to hotel departments.
5. Operators to authenticate.
6. Operators to view requests belonging to their department.
7. Operators to update request status.
8. Operators to record the resolution of requests.
9. All request data to be persisted in PostgreSQL.
10. Administrators to manage core system entities through Django Admin.

AI, notifications, advanced analytics, and containerization are outside the current MVP scope.

---

## Main Actors

### Guest

Can:

- Authenticate
- View profile
- Create requests
- View own requests
- View request details
- Track request status

### Operator

Can:

- Authenticate
- View requests assigned to their department
- View request details
- Update request status
- Record resolution

### Administrator

Can:

- Manage users
- Manage guests
- Manage operators
- Manage departments
- Manage rooms
- Manage request categories
- Manage tickets

### Department Manager

Planned for a future version.

### Hotel Manager

Planned for a future version.

### AI Agent

Planned for a future version.

The AI Agent will eventually analyze guest requests and assist with:

- Category classification
- Department routing
- Priority detection
- Request classification

---

## Core Modules

### Current MVP

- Authentication
- Guest Management
- Room Management
- Department Management
- Request Category Management
- Ticket Management
- Operator Management
- Authorization
- Django Admin
- REST API
- API Documentation
- Automated Testing

### Future

- AI Routing
- AI Classification
- Notification System
- Analytics
- Reporting
- Advanced Dashboards
- Operational Intelligence

---

## Architecture

The project currently follows a:

**Modular Monolith + API-First Architecture**

The application is organized into independent Django modules with clear separation of responsibilities.

The architecture should remain modular and maintainable so that individual components can be extracted or scaled independently in the future if required.

The project follows these principles:

- Separation of Concerns
- Domain-oriented modularization
- API First
- Clean Code
- SOLID where appropriate
- Secure by Default
- Testability
- Scalability
- Avoidance of unnecessary Overengineering

Clean Architecture and Domain-Driven Design principles may be applied where they provide practical value, but the MVP must remain simple and maintainable.

---

## Technology Stack

### Backend

- Python 3.13
- Django
- Django REST Framework

### ORM

- Django ORM

### Database

- PostgreSQL 17

### Authentication

- JWT
- djangorestframework-simplejwt

### API Documentation

- OpenAPI
- drf-spectacular
- Swagger
- ReDoc

### Frontend

The frontend is outside the current MVP implementation scope.

The planned frontend technology is:

- Next.js
- TypeScript

The backend must remain API-first so that the frontend can be developed independently.

---

## Development Environment

The MVP is developed locally without Docker.

Development stack:

```text
Python 3.13
    |
Virtual Environment
    |
Django
    |
Django REST Framework
    |
PostgreSQL 17
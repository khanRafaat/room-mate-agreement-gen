# Roommate Agreement Generator - Frontend Integration Guide (Next.js)

> **Purpose**: This document provides complete API documentation for building a Next.js frontend. The backend is a Python FastAPI application. Follow this guide exactly to avoid integration mistakes.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Service Setup (CRITICAL)](#api-service-setup-critical)
3. [Authentication Flow](#authentication-flow)
4. [Complete API Reference](#complete-api-reference)
5. [Data Models & TypeScript Interfaces](#data-models--typescript-interfaces)
6. [User Flow & State Machine](#user-flow--state-machine)
7. [Error Handling](#error-handling)
8. [File Upload Flow](#file-upload-flow)
9. [Environment Variables](#environment-variables)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     NEXT.JS FRONTEND                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Pages/     │  │  Components/ │  │  Services/           │  │
│  │   App Router │  │  UI Layer    │  │  API Layer           │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 FASTAPI BACKEND (Python)                        │
│  Base URL: http://localhost:8000 (dev) | https://api.domain.com │
│                                                                 │
│  /api/auth/*      - Authentication                              │
│  /api/agreements/* - Agreement CRUD                             │
│  /api/users/*     - User profile & ID verification              │
│  /api/invites/*   - Invite management                           │
│  /api/feedback/*  - Roommate ratings                            │
│  /api/files/*     - File upload/download                        │
│  /api/webhooks/*  - Payment/Signature webhooks                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Service Setup (CRITICAL)

> [!CAUTION]
> **ALL API calls MUST go through a centralized service layer with a configurable base URL. This is mandatory.**

### File: `services/api.ts`

```typescript
// API Configuration - Base URL must be configurable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

// Token storage keys
const TOKEN_KEY = 'auth_token';

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  // Get stored token
  private getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(TOKEN_KEY);
    }
    return null;
  }

  // Set token
  setToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem(TOKEN_KEY, token);
    }
  }

  // Clear token (logout)
  clearToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
    }
  }

  // Build headers with authentication
  private getHeaders(includeAuth: boolean = true): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (includeAuth) {
      const token = this.getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }
    
    return headers;
  }

  // Generic request method
  async request<T>(
    endpoint: string,
    options: {
      method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
      body?: any;
      auth?: boolean;
    } = {}
  ): Promise<T> {
    const { method = 'GET', body, auth = true } = options;
    
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      method,
      headers: this.getHeaders(auth),
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new ApiError(response.status, error.detail || 'Request failed');
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return null as T;
    }

    return response.json();
  }

  // Convenience methods
  get<T>(endpoint: string, auth = true) {
    return this.request<T>(endpoint, { method: 'GET', auth });
  }

  post<T>(endpoint: string, body: any, auth = true) {
    return this.request<T>(endpoint, { method: 'POST', body, auth });
  }

  patch<T>(endpoint: string, body: any, auth = true) {
    return this.request<T>(endpoint, { method: 'PATCH', body, auth });
  }

  delete<T>(endpoint: string, auth = true) {
    return this.request<T>(endpoint, { method: 'DELETE', auth });
  }
}

// Custom error class
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

// Export singleton instance
export const api = new ApiService(API_BASE_URL);
```

---

## Authentication Flow

### JWT Token Format

The backend uses JWT tokens. After login/register, store the token and send it with every authenticated request.

```
Authorization: Bearer <jwt_token>
```

### Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | No | Create new user account |
| POST | `/api/auth/login` | No | Login with email/password |
| GET | `/api/auth/me` | Yes | Get current user profile |
| POST | `/api/auth/refresh` | Yes | Refresh JWT token |
| POST | `/api/auth/change-password` | Yes | Change password |
| POST | `/api/auth/logout` | Yes | Logout (client discards token) |

### File: `services/authService.ts`

```typescript
import { api, ApiError } from './api';
import { 
  UserRegister, 
  UserLogin, 
  AuthResponse, 
  UserAuthResponse, 
  Token 
} from '@/types';

export const authService = {
  // Register new user
  async register(data: UserRegister): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/api/auth/register', data, false);
    api.setToken(response.token.access_token);
    return response;
  },

  // Login
  async login(data: UserLogin): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/api/auth/login', data, false);
    api.setToken(response.token.access_token);
    return response;
  },

  // Get current user
  async getMe(): Promise<UserAuthResponse> {
    return api.get<UserAuthResponse>('/api/auth/me');
  },

  // Refresh token
  async refreshToken(): Promise<Token> {
    return api.post<Token>('/api/auth/refresh', {});
  },

  // Change password
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/api/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },

  // Logout
  logout(): void {
    api.clearToken();
  },
};
```

---

## Complete API Reference

### 1. Authentication (`/api/auth`)

#### POST `/api/auth/register`
Create a new user account.

**Request Body:**
```typescript
{
  email: string;          // Valid email (unique)
  password: string;       // Min 6 characters
  name?: string;          // Optional display name
  phone?: string;         // Optional phone
}
```

**Response (201):**
```typescript
{
  user: {
    id: string;
    email: string;
    name: string | null;
    phone: string | null;
    is_verified: boolean;
    created_at: string;   // ISO datetime
  };
  token: {
    access_token: string;
    token_type: "bearer";
    expires_in: number;   // seconds
  };
}
```

---

#### POST `/api/auth/login`
Login with email and password.

**Request Body:**
```typescript
{
  email: string;
  password: string;
}
```

**Response (200):**
```typescript
// Same as register response
{
  user: UserAuthResponse;
  token: Token;
}
```

**Errors:**
- `401`: Incorrect email or password

---

#### GET `/api/auth/me`
Get current authenticated user profile.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```typescript
{
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  is_verified: boolean;
  created_at: string;
}
```

---

#### POST `/api/auth/refresh`
Refresh the JWT access token.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```typescript
{
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}
```

---

#### POST `/api/auth/change-password`
Change user's password.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```typescript
{
  current_password: string;
  new_password: string;  // Min 6 characters
}
```

**Response (200):**
```typescript
{ message: "Password changed successfully" }
```

---

### 2. Users (`/api/users`)

#### GET `/api/users/me`
Get current user's full profile.

**Response (200):**
```typescript
{
  id: string;           // UUID
  email: string;
  phone: string | null;
  is_verified: boolean;
  created_at: string;
}
```

---

#### PATCH `/api/users/me`
Update user profile.

**Query Params:**
- `phone` (optional): New phone number
- `name` (optional): New display name

**Response (200):** Updated user object

---

#### POST `/api/users/verify`
Start ID verification process (ID.me, Onfido, or Persona).

> [!IMPORTANT]
> Users MUST be verified before creating agreements!

**Request Body:**
```typescript
{
  provider: "idme" | "onfido" | "persona";
}
```

**Response (200):**
```typescript
{
  verification_id: string;
  provider: string;
  redirect_url: string;  // Redirect user here to verify
}
```

---

#### GET `/api/users/verify/status`
Get all verification records for current user.

**Response (200):**
```typescript
[
  {
    id: string;
    provider: string;
    status: "pending" | "approved" | "rejected";
    reference_id: string | null;
    completed_at: string | null;
    created_at: string;
  }
]
```

---

#### GET `/api/users/verify/{verification_id}`
Get specific verification record.

**Response (200):** Single verification object

---

### 3. Agreements (`/api/agreements`)

> [!WARNING]
> Most agreement endpoints require user to be ID verified (`is_verified: true`). Exceptions are noted below.

#### POST `/api/agreements`
Create a new agreement (draft status).

**Request Body:**
```typescript
{
  title?: string;                    // Default: "Roommate Agreement"
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  start_date?: string;               // "YYYY-MM-DD"
  end_date?: string;                 // "YYYY-MM-DD"
  rent_total_cents: number;          // REQUIRED - Total rent in cents
  terms?: {
    quiet_hours?: { start: string; end: string };      // e.g., "22:00", "07:00"
    guest_rules?: { max_consecutive_nights: number; notice_hours: number };
    pet_rules?: { allowed: boolean; notes?: string };
    deposit_cents?: number;
    deposit_forfeit_reasons?: string[];
    additional_rules?: string;
    no_offensive_clause_ack?: boolean;
  };
  parties?: [
    {
      email: string;
      phone?: string;
      role?: "roommate";
      rent_share_cents?: number;
      utilities?: Record<string, any>;
      chores?: Record<string, any>;
    }
  ];
}
```

**Response (201):**
```typescript
{
  id: string;                        // UUID
  initiator_id: string;
  title: string;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  start_date: string | null;
  end_date: string | null;
  rent_total_cents: number;
  status: "draft";
  created_at: string;
  terms: AgreementTerms | null;
  parties: AgreementParty[];
}
```

---

#### GET `/api/agreements`
List all agreements for current user.

> [!NOTE]
> This endpoint does NOT require ID verification (unlike most other agreement endpoints).

**Response (200):**
```typescript
[
  {
    id: string;
    title: string;
    address_line1: string | null;
    city: string | null;
    state: string | null;
    status: string;
    start_date: string | null;
    end_date: string | null;
    created_at: string;
  }
]
```

---

#### GET `/api/agreements/{agreement_id}`
Get full agreement details.

**Response (200):** Full agreement object with terms and parties

---

#### PATCH `/api/agreements/{agreement_id}`
Update agreement (only in draft status).

**Request Body:** Same fields as create (all optional)

**Response (200):** Updated agreement

**Errors:**
- `400`: Cannot update after payment

---

#### POST `/api/agreements/{agreement_id}/finalize`
Finalize draft and move to `awaiting_payment` status.

**Response (200):**
```typescript
{
  ok: true;
  status: "awaiting_payment";
  message: string;
}
```

---

#### POST `/api/agreements/{agreement_id}/pay`
Get payment checkout links.

> [!NOTE]
> Agreement must be finalized first (status = `awaiting_payment`)

**Response (200):**
```typescript
{
  card: {
    payment_id: string;
    method: "card";
    checkout_url: string;        // Redirect to Stripe
  } | null;
  crypto: {
    payment_id: string;
    method: "solana";
    checkout_url: string;        // Redirect to Coinbase Commerce
  } | null;
}
```

---

#### POST `/api/agreements/{agreement_id}/invite`
Invite roommates via email (requires payment completed).

**Request Body:**
```typescript
{
  roommates: [
    {
      email: string;             // REQUIRED
      phone?: string;
      role?: "roommate";
      rent_share_cents?: number;
      utilities?: Record<string, any>;
      chores?: Record<string, any>;
    }
  ]
}
```

**Response (200):**
```typescript
[
  {
    token: string;
    email: string;
    expires_at: string;
    invite_url: string;          // Full URL for roommate to accept
  }
]
```

**Errors:**
- `402`: Payment required

---

#### POST `/api/agreements/{agreement_id}/docusign/envelope`
Create DocuSign envelope for signing.

> [!NOTE]
> All invited roommates must have joined before creating envelope.

**Response (200):**
```typescript
{
  ok: true;
  message: string;
  agreement_id: string;
  status: "signing";
}
```

---

#### GET `/api/agreements/{agreement_id}/signlink`
Get embedded signing link for current user.

**Response (200):**
```typescript
{
  ok: true;
  message: string;
  agreement_id: string;
}
```

---

#### POST `/api/agreements/{agreement_id}/complete`
Mark agreement as completed (all signatures received).

> [!NOTE]
> This endpoint does NOT require ID verification.

**Response (200):**
```typescript
{
  ok: true;
  status: "completed";
  message: string;
}
```

---

### 4. Invites (`/api/invites`)

#### GET `/api/invites/accept/{token}` (Public)
Get invite information by token (no auth required).

**Response (200):**
```typescript
{
  valid: true;
  email: string;
  agreement_id: string;
  agreement_title: string;
  expires_at: string;
  user_exists: boolean;
  user_verified: boolean;
  next_step: "login" | "verify" | "register";
}
```

---

#### POST `/api/invites/accept/{token}`
Accept invite and join agreement.

> [!IMPORTANT]
> User must be logged in AND verified to accept an invite

**Response (200):**
```typescript
{
  success: true;
  message: string;
  agreement_id: string;
}
```

**Errors:**
- `403`: User not verified
- `400`: Wrong email / expired / already used

---

#### GET `/api/invites/my-invites`
Get all pending invites for current user's email.

**Response (200):**
```typescript
[
  {
    token: string;
    agreement_id: string;
    agreement_title: string;
    invited_by: string;
    expires_at: string;
  }
]
```

---

#### DELETE `/api/invites/{token}`
Revoke an invite (initiator only).

**Response (200):**
```typescript
{ success: true; message: string; }
```

---

### 5. Feedback (`/api/feedback`)

#### POST `/api/feedback/{agreement_id}`
Submit feedback for a roommate.

> [!NOTE]
> Agreement must be completed. Can only rate other parties, not yourself.

**Request Body:**
```typescript
{
  to_user_id: string;              // REQUIRED - UUID of roommate to rate
  rating: number;                  // REQUIRED - 1-5 stars
  comment?: string;                // Max 1000 chars
  categories?: {
    cleanliness?: number;          // 1-5
    communication?: number;        // 1-5
    respect?: number;              // 1-5
    reliability?: number;          // 1-5
    noise_level?: number;          // 1-5
  };
  is_anonymous?: boolean;          // Default: false
}
```

**Response (201):**
```typescript
{
  id: string;
  agreement_id: string;
  from_user_id: string | null;     // null if anonymous
  from_user_name: string | null;
  to_user_id: string;
  to_user_name: string | null;
  rating: number;
  comment: string | null;
  categories: Record<string, number> | null;
  is_anonymous: boolean;
  created_at: string;
}
```

---

#### GET `/api/feedback/{agreement_id}`
Get all feedback for an agreement (parties only).

**Response (200):** Array of feedback objects

---

#### GET `/api/feedback/user/{user_id}/summary`
Get feedback summary for a user.

**Response (200):**
```typescript
{
  user_id: string;
  user_name: string | null;
  total_ratings: number;
  average_rating: number;          // e.g., 4.5
  category_averages: {
    cleanliness?: number;
    communication?: number;
    // ... etc
  } | null;
  recent_feedback: FeedbackResponse[];  // Last 5
}
```

---

#### DELETE `/api/feedback/{feedback_id}`
Delete your own feedback.

**Response (204):** No content

---

### 6. Files (`/api`)

#### POST `/api/upload-sas`
Get SAS token for uploading file to Azure Blob Storage.

**Request Body:**
```typescript
{
  kind: "lease_first_page" | "govt_id" | "agreement_pdf" | "signed_pdf";
  filename: string;                // Original filename
}
```

**Response (200):**
```typescript
{
  url: string;                     // Pre-signed upload URL
  blob_name: string;               // Generated blob name
  expires_at: string;              // Token expiry
}
```

---

#### POST `/api/upload-complete`
Confirm upload completion (create file record).

**Request Body:**
```typescript
{
  blob_name: string;               // From upload-sas response
  kind: string;
  size_bytes: number;
  container?: string;              // Default: "agreements"
}
```

**Response (200):**
```typescript
{
  id: string;                      // File asset ID
  owner_id: string;
  kind: string;
  container: string;
  blob_name: string;
  size_bytes: number;
  created_at: string;
}
```

---

#### GET `/api/files/{file_id}/sas`
Get SAS token for downloading file.

**Response (200):**
```typescript
{
  url: string;                     // Pre-signed download URL (60 min TTL)
  blob_name: string;
  expires_at: string;
}
```

---

#### GET `/api/files`
List files owned by current user.

**Query Params:**
- `kind` (optional): Filter by file kind

**Response (200):** Array of file asset objects

---

#### DELETE `/api/files/{file_id}`
Delete a file (record and blob).

**Response (204):** No content

---

### 7. Webhooks (`/api/webhooks`) - Backend Only

> [!NOTE]
> These endpoints are called by external services (Stripe, Coinbase, DocuSign). Not for frontend use.

| Endpoint | Source |
|----------|--------|
| POST `/api/webhooks/stripe` | Stripe payment events |
| POST `/api/webhooks/coinbase` | Coinbase Commerce events |
| POST `/api/webhooks/docusign` | DocuSign envelope events |
| POST `/api/webhooks/kyc/{provider}` | KYC verification events |

---

## Data Models & TypeScript Interfaces

### File: `types/index.ts`

```typescript
// ==================== AUTH ====================

export interface UserRegister {
  email: string;
  password: string;
  name?: string;
  phone?: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserAuthResponse {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  is_verified: boolean;
  created_at: string;
}

export interface AuthResponse {
  user: UserAuthResponse;
  token: Token;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

// ==================== USER ====================

// NOTE: UserResponse (from /api/users/me) does NOT include 'name' field
// Use UserAuthResponse (from /api/auth/me) if you need the name field
export interface UserResponse {
  id: string;
  email: string;
  phone: string | null;
  is_verified: boolean;
  created_at: string;
}

export interface IdVerificationCreate {
  provider: 'idme' | 'onfido' | 'persona';
}

export interface IdVerificationResponse {
  id: string;
  provider: string;
  status: 'pending' | 'approved' | 'rejected';
  reference_id: string | null;
  completed_at: string | null;
  created_at: string;
}

// ==================== AGREEMENT ====================

export interface QuietHours {
  start: string;  // "HH:mm"
  end: string;
}

export interface GuestRules {
  max_consecutive_nights: number;
  notice_hours: number;
}

export interface PetRules {
  allowed: boolean;
  notes?: string;
}

export interface AgreementTerms {
  quiet_hours?: QuietHours;
  guest_rules?: GuestRules;
  pet_rules?: PetRules;
  deposit_cents?: number;
  deposit_forfeit_reasons?: string[];
  additional_rules?: string;
  no_offensive_clause_ack?: boolean;
}

export interface AgreementParty {
  id: string;
  user_id: string | null;
  email: string;
  phone: string | null;
  role: 'initiator' | 'roommate';
  rent_share_cents: number | null;
  utilities: Record<string, any> | null;
  chores: Record<string, any> | null;
  signed: boolean;
  signed_at: string | null;
}

export interface AgreementPartyCreate {
  email: string;
  phone?: string;
  role?: 'roommate';
  rent_share_cents?: number;
  utilities?: Record<string, any>;
  chores?: Record<string, any>;
}

export type AgreementStatus = 
  | 'draft'
  | 'awaiting_payment'
  | 'paid'
  | 'inviting'
  | 'signing'
  | 'completed'
  | 'void';

export interface AgreementCreate {
  title?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  start_date?: string;
  end_date?: string;
  rent_total_cents: number;
  terms?: AgreementTerms;
  parties?: AgreementPartyCreate[];
}

export interface AgreementResponse {
  id: string;
  initiator_id: string;
  title: string;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  start_date: string | null;
  end_date: string | null;
  rent_total_cents: number;
  status: AgreementStatus;
  created_at: string;
  terms: AgreementTerms | null;
  parties: AgreementParty[];
}

export interface AgreementListResponse {
  id: string;
  title: string;
  address_line1: string | null;
  city: string | null;
  state: string | null;
  status: AgreementStatus;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
}

export interface AgreementUpdate {
  title?: string;
  address_line1?: string;
  address_line2?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  start_date?: string;
  end_date?: string;
  rent_total_cents?: number;
}

export interface InviteRequest {
  roommates: AgreementPartyCreate[];
}

// ==================== PAYMENT ====================

export interface CheckoutResponse {
  payment_id: string;
  method: 'card' | 'solana';
  checkout_url: string;
}

export interface CheckoutLinks {
  card: CheckoutResponse | null;
  crypto: CheckoutResponse | null;
}

// ==================== INVITE ====================

export interface InviteTokenResponse {
  token: string;
  email: string;
  expires_at: string;
  invite_url: string;
}

export interface InviteInfo {
  valid: boolean;
  email: string;
  agreement_id: string;
  agreement_title: string;
  expires_at: string;
  user_exists: boolean;
  user_verified: boolean;
  next_step: 'login' | 'verify' | 'register';
}

export interface PendingInvite {
  token: string;
  agreement_id: string;
  agreement_title: string;
  invited_by: string;
  expires_at: string;
}

// ==================== FEEDBACK ====================

export interface CategoryRatings {
  cleanliness?: number;
  communication?: number;
  respect?: number;
  reliability?: number;
  noise_level?: number;
}

export interface FeedbackCreate {
  to_user_id: string;
  rating: number;
  comment?: string;
  categories?: CategoryRatings;
  is_anonymous?: boolean;
}

export interface FeedbackResponse {
  id: string;
  agreement_id: string;
  from_user_id: string | null;
  from_user_name: string | null;
  to_user_id: string;
  to_user_name: string | null;
  rating: number;
  comment: string | null;
  categories: Record<string, number> | null;
  is_anonymous: boolean;
  created_at: string;
}

export interface FeedbackSummary {
  user_id: string;
  user_name: string | null;
  total_ratings: number;
  average_rating: number;
  category_averages: Record<string, number> | null;
  recent_feedback: FeedbackResponse[];
}

// ==================== FILES ====================

export interface SASRequest {
  kind: 'lease_first_page' | 'govt_id' | 'agreement_pdf' | 'signed_pdf';
  filename: string;
}

export interface SASResponse {
  url: string;
  blob_name: string;
  expires_at: string;
}

export interface UploadComplete {
  blob_name: string;
  kind: string;
  size_bytes: number;
  container?: string;
}

export interface FileAssetResponse {
  id: string;
  owner_id: string;
  kind: string;
  container: string;
  blob_name: string;
  size_bytes: number | null;
  created_at: string;
}
```

---

## User Flow & State Machine

### Agreement Status Flow

```
┌──────────┐     finalize     ┌───────────────────┐
│  draft   │ ─────────────────▶ awaiting_payment  │
└──────────┘                  └─────────┬─────────┘
                                        │ payment webhook
                                        ▼
┌───────────┐     invite       ┌───────────────────┐
│  inviting │ ◀────────────────│       paid        │
└─────┬─────┘                  └───────────────────┘
      │ all roommates joined
      ▼
┌───────────┐   docusign       ┌───────────────────┐
│  signing  │ ◀──envelope──────│  (auto transition)│
└─────┬─────┘                  └───────────────────┘
      │ all signed (webhook)
      ▼
┌───────────┐                  ┌───────────────────┐
│ completed │                  │       void        │
└───────────┘                  └───────────────────┘
```

### Complete User Journey

```
1. REGISTER
   POST /api/auth/register
   ↓
2. ID VERIFICATION (Required)
   POST /api/users/verify
   → Redirect to ID.me/Onfido/Persona
   → Wait for webhook to update is_verified
   ↓
3. CREATE AGREEMENT
   POST /api/agreements
   → Status: "draft"
   ↓
4. UPLOAD FILES (Optional)
   POST /api/upload-sas
   → Upload to Azure Blob
   POST /api/upload-complete
   ↓
5. FINALIZE DRAFT
   POST /api/agreements/{id}/finalize
   → Status: "awaiting_payment"
   ↓
6. PAY
   POST /api/agreements/{id}/pay
   → Get checkout URLs
   → Redirect to Stripe/Coinbase
   → Wait for payment webhook
   → Status: "paid" → "inviting"
   ↓
7. INVITE ROOMMATES
   POST /api/agreements/{id}/invite
   → Emails sent to roommates
   ↓
8. ROOMMATE ACCEPTS (each roommate)
   GET /api/invites/accept/{token}  (check status)
   → If not registered: Register first
   → If not verified: Verify first
   POST /api/invites/accept/{token}
   ↓
9. CREATE SIGNING ENVELOPE
   POST /api/agreements/{id}/docusign/envelope
   → Status: "signing"
   ↓
10. SIGN AGREEMENT (each party)
    GET /api/agreements/{id}/signlink
    → Redirect to DocuSign
    → Wait for DocuSign webhook
    ↓
11. COMPLETED
    → Status: "completed" (via webhook)
    ↓
12. LEAVE FEEDBACK
    POST /api/feedback/{agreement_id}
```

---

## Error Handling

### Standard Error Response

All errors return:
```typescript
{
  detail: string;  // Error message
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid/missing token |
| 402 | Payment Required - Must pay first |
| 403 | Forbidden - Not verified / No access |
| 404 | Not Found - Resource doesn't exist |
| 500 | Server Error |

### Example Error Handling

```typescript
import { ApiError } from '@/services/api';

try {
  await agreementService.create(data);
} catch (error) {
  if (error instanceof ApiError) {
    switch (error.status) {
      case 401:
        // Redirect to login
        router.push('/login');
        break;
      case 403:
        // Not verified
        toast.error('Please complete ID verification first');
        router.push('/verify');
        break;
      case 402:
        // Payment required
        toast.error('Please complete payment first');
        break;
      default:
        toast.error(error.message);
    }
  }
}
```

---

## File Upload Flow

### Direct-to-Blob Upload

```typescript
// services/fileService.ts

export const fileService = {
  async uploadFile(file: File, kind: SASRequest['kind']): Promise<FileAssetResponse> {
    // 1. Get SAS token
    const { url, blob_name } = await api.post<SASResponse>('/api/upload-sas', {
      kind,
      filename: file.name,
    });

    // 2. Upload directly to Azure Blob
    const uploadResponse = await fetch(url, {
      method: 'PUT',
      headers: {
        'x-ms-blob-type': 'BlockBlob',
        'Content-Type': file.type,
      },
      body: file,
    });

    if (!uploadResponse.ok) {
      throw new Error('Upload failed');
    }

    // 3. Confirm upload - determine correct container
    let container = 'agreements';
    if (kind === 'govt_id') container = 'ids';
    else if (kind === 'signed_pdf') container = 'signed';

    return api.post<FileAssetResponse>('/api/upload-complete', {
      blob_name,
      kind,
      size_bytes: file.size,
      container,
    });
  },

  async downloadFile(fileId: string): Promise<string> {
    const { url } = await api.get<SASResponse>(`/api/files/${fileId}/sas`);
    return url;
  },
};
```

---

## Environment Variables

### File: `.env.local`

```bash
# REQUIRED - API Base URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# For production
# NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.com
```

> [!CAUTION]
> Never hardcode the API URL. Always use the environment variable to allow easy switching between environments.

---

## Service Files Summary

Create these service files in `services/` directory:

| File | Description |
|------|-------------|
| `api.ts` | Base API service with auth handling |
| `authService.ts` | Authentication methods |
| `userService.ts` | User profile & ID verification |
| `agreementService.ts` | Agreement CRUD |
| `inviteService.ts` | Invite management |
| `feedbackService.ts` | Roommate ratings |
| `fileService.ts` | File upload/download |

### Service Pattern Example

```typescript
// services/agreementService.ts
import { api } from './api';
import { 
  AgreementCreate, 
  AgreementResponse, 
  AgreementListResponse,
  AgreementUpdate,
  CheckoutLinks,
  InviteRequest,
  InviteTokenResponse
} from '@/types';

export const agreementService = {
  create: (data: AgreementCreate) => 
    api.post<AgreementResponse>('/api/agreements', data),

  list: () => 
    api.get<AgreementListResponse[]>('/api/agreements'),

  get: (id: string) => 
    api.get<AgreementResponse>(`/api/agreements/${id}`),

  update: (id: string, data: AgreementUpdate) => 
    api.patch<AgreementResponse>(`/api/agreements/${id}`, data),

  finalize: (id: string) => 
    api.post<{ ok: boolean; status: string; message: string }>(
      `/api/agreements/${id}/finalize`, 
      {}
    ),

  getPaymentLinks: (id: string) => 
    api.post<CheckoutLinks>(`/api/agreements/${id}/pay`, {}),

  invite: (id: string, data: InviteRequest) => 
    api.post<InviteTokenResponse[]>(`/api/agreements/${id}/invite`, data),

  createEnvelope: (id: string) => 
    api.post<{ ok: boolean; message: string; agreement_id: string; status: string }>(
      `/api/agreements/${id}/docusign/envelope`, 
      {}
    ),

  getSignLink: (id: string) => 
    api.get<{ ok: boolean; message: string; agreement_id: string }>(
      `/api/agreements/${id}/signlink`
    ),

  complete: (id: string) => 
    api.post<{ ok: boolean; status: string; message: string }>(
      `/api/agreements/${id}/complete`, 
      {}
    ),
};
```

---

## Backend Server Info

- **Run Command**: `uvicorn app.main:app --reload`
- **Default Port**: `8000`
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Health Check**: `GET /healthz`

---

> [!TIP]
> Run the backend with `--reload` during development for auto-reload on code changes.

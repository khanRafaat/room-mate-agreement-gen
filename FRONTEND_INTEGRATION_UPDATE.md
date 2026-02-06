# Frontend Integration Updates - Base Agreement Feature

> **Purpose**: This document describes the API and UI changes needed to support the new **Country → State → City → Base Agreement** feature. Use this alongside the existing `FRONTEND_INTEGRATION.md`.
>
> **Status**: ✅ All backend endpoints are LIVE and verified working!

---

## Table of Contents

1. [Summary of Changes](#summary-of-changes)
2. [New API Endpoints - Locations](#new-api-endpoints---locations)
3. [New API Endpoints - Base Agreements](#new-api-endpoints---base-agreements)
4. [Updated Agreement Endpoints](#updated-agreement-endpoints)
5. [TypeScript Interfaces](#typescript-interfaces)
6. [Service Files](#service-files)
7. [Updated User Flow](#updated-user-flow)
8. [UI Components](#ui-components)
9. [Sample API Responses](#sample-api-responses)

---

## Summary of Changes

| Area | What Changed |
|------|--------------|
| **New Endpoints** | 10 new endpoints (locations + base agreements) |
| **Updated Endpoints** | `POST /api/agreements` accepts `base_agreement_id`, `owner_name` |
| **New TypeScript Types** | Country, State, City, BaseAgreement interfaces |
| **New UI Components** | Cascading dropdown selectors, agreement preview |
| **Updated User Flow** | Location selection BEFORE agreement creation |

---

## New API Endpoints - Locations

> [!NOTE]
> Location endpoints are **public** (no authentication required) for better UX.

### GET `/api/locations/countries`

Get all active countries for dropdown (sorted alphabetically).

**Response (200):**
```typescript
Country[]  // Array of 26 countries
```

**Example Response:**
```json
[
  { "id": "28ce4960-f950-454a-84b4-c1c2e919bab3", "code": "US", "name": "United States" },
  { "id": "e1a806fb-e834-48b5-8c46-54ee8a2f370f", "code": "BD", "name": "Bangladesh" },
  { "id": "8344b5f3-527c-42e6-abaf-331dde113044", "code": "GB", "name": "United Kingdom" }
]
```

---

### GET `/api/locations/countries/{country_id}`

Get a specific country by ID.

**Response (200):** Single `Country` object

**Errors:** `404` - Country not found

---

### GET `/api/locations/countries/{country_id}/states`

Get states/provinces for a country (cascading dropdown).

**Response (200):**
```typescript
State[]  // E.g., 51 US states, 8 Bangladesh divisions
```

**Example Response (USA):**
```json
[
  { "id": "828ef706-cd22-4d04-96a6-bcf5dbf24e17", "country_id": "28ce4960-...", "code": "CA", "name": "California" },
  { "id": "904d9ed8-d95d-4d46-bb2c-28c61425eee2", "country_id": "28ce4960-...", "code": "NY", "name": "New York" }
]
```

---

### GET `/api/locations/states/{state_id}`

Get a specific state by ID.

**Response (200):** Single `State` object

---

### GET `/api/locations/states/{state_id}/cities`

Get cities for a state (cascading dropdown).

**Response (200):**
```typescript
City[]  // E.g., 14 California cities
```

**Example Response (California):**
```json
[
  { "id": "7adb0e45-10c7-45d8-a11b-27a089e34f11", "state_id": "828ef706-...", "name": "Los Angeles" },
  { "id": "c9c38f7b-bb0f-49c5-a797-73800b1eb14d", "state_id": "828ef706-...", "name": "San Francisco" }
]
```

---

### GET `/api/locations/cities/{city_id}`

Get a specific city by ID.

**Response (200):** Single `City` object

---

## New API Endpoints - Base Agreements

### GET `/api/base-agreements/city/{city_id}` (Public)

Get the active base agreement for a city. **This is the main endpoint for the frontend.**

**Response (200):**
```typescript
{
  id: string;
  city_id: string;
  city_name: string;
  state_name: string;
  country_name: string;
  title: string;           // "Los Angeles Roommate Agreement"
  version: string;         // "1.0.0"
  content: string | null;  // Full agreement text (if text-based)
  applicable_for: "landlord" | "tenant" | "both";
  is_active: boolean;
  effective_date: string | null;
  created_at: string;
  
  // PDF file info (NEW)
  pdf_filename: string | null;   // Original filename
  pdf_size_bytes: number | null; // File size in bytes
  pdf_url: string | null;        // Pre-signed download URL (valid 60 min)
  has_pdf: boolean;              // Quick check if PDF is attached
}
```

**Errors:**
- `404`: City not found
- `404`: No base agreement found for this city

---

### GET `/api/base-agreements/{agreement_id}`

Get a specific base agreement by ID.

**Response (200):** Same as above

---

### GET `/api/base-agreements` (Auth Required)

List all base agreements (admin endpoint).

**Query Params:**
- `city_id` (optional): Filter by city
- `is_active` (optional): Filter by active status

**Response (200):**
```typescript
BaseAgreementSummary[]  // Max 100 results
```

---

### POST `/api/base-agreements` (Auth Required)

Create a new base agreement (admin endpoint).

**Request Body:**
```typescript
{
  city_id: string;                    // REQUIRED
  title: string;                      // REQUIRED
  version?: string;                   // Default: "1.0.0"
  content?: string;                   // Agreement text
  applicable_for?: "landlord" | "tenant" | "both";  // Default: "both"
  effective_date?: string;            // "YYYY-MM-DD"
}
```

**Response (201):** Full `BaseAgreementResponse`

---

### PATCH `/api/base-agreements/{id}` (Auth Required)

Update a base agreement (admin endpoint).

**Request Body:**
```typescript
{
  title?: string;
  version?: string;
  content?: string;
  applicable_for?: string;
  is_active?: boolean;
  effective_date?: string;
}
```

**Response (200):** Updated `BaseAgreementResponse`

---

### DELETE `/api/base-agreements/{id}` (Auth Required)

Delete a base agreement (admin endpoint).

**Response (204):** No content

**Errors:**
- `400`: Cannot delete - linked to existing agreements (deactivate instead)
- `404`: Not found

---

### POST `/api/base-agreements/{id}/deactivate` (Auth Required)

Deactivate a base agreement (soft delete).

**Response (200):** Updated `BaseAgreementResponse` with `is_active: false`

---

### POST `/api/base-agreements/{id}/activate` (Auth Required)

Reactivate a base agreement.

**Response (200):** Updated `BaseAgreementResponse` with `is_active: true`

---

## PDF Upload Endpoints (NEW)

> [!NOTE]
> Base agreements can have a PDF/DOC file attached. When a user selects a city, they can view/download the PDF.

### POST `/api/base-agreements/{id}/pdf/upload-sas` (Auth Required)

Get a pre-signed URL to upload a PDF to Azure Blob Storage.

**Query Params:**
- `filename` (required): Original filename (e.g., "LA_Agreement.pdf")

**Allowed file types:** `.pdf`, `.doc`, `.docx`

**Response (200):**
```typescript
{
  url: string;           // Pre-signed upload URL (valid 15 minutes)
  blob_name: string;     // Internal blob path
  container: string;     // "base-agreements"
  expires_at: string;    // ISO timestamp
}
```

**Frontend Upload Flow:**
```typescript
// 1. Get upload URL
const sasResponse = await fetch(
  `/api/base-agreements/${id}/pdf/upload-sas?filename=${file.name}`,
  { headers: { Authorization: `Bearer ${token}` } }
);
const { url, blob_name, container } = await sasResponse.json();

// 2. Upload directly to Azure
await fetch(url, {
  method: 'PUT',
  headers: { 'x-ms-blob-type': 'BlockBlob' },
  body: file
});

// 3. Confirm upload
await fetch(`/api/base-agreements/${id}/pdf`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`
  },
  body: JSON.stringify({
    blob_name,
    filename: file.name,
    size_bytes: file.size,
    container
  })
});
```

---

### POST `/api/base-agreements/{id}/pdf` (Auth Required)

Attach an uploaded PDF to the base agreement (call after upload completes).

**Request Body:**
```typescript
{
  blob_name: string;      // From upload-sas response
  filename: string;       // Original filename
  size_bytes: number;     // File size
  container?: string;     // Default: "base-agreements"
}
```

**Response (200):** Updated `BaseAgreementResponse` with PDF info

---

### GET `/api/base-agreements/{id}/pdf/download-sas` (Public)

Get a pre-signed URL to download the PDF (valid 60 minutes).

**Response (200):**
```typescript
{
  url: string;           // Pre-signed download URL
  filename: string;      // Original filename
  size_bytes: number;    // File size
  expires_at: string;    // ISO timestamp
}
```

**Errors:**
- `404`: No PDF attached to this agreement

---

### DELETE `/api/base-agreements/{id}/pdf` (Auth Required)

Remove the PDF from a base agreement.

**Response (200):** Updated `BaseAgreementResponse` with PDF cleared

---

## Updated Agreement Endpoints

### POST `/api/agreements` - UPDATED

**New Request Fields:**
```typescript
{
  // ... existing fields (title, address, rent_total_cents, etc.) ...
  
  base_agreement_id?: string;    // Link to city-specific base agreement
  owner_name?: string;           // Landlord's full legal name
}
```

---

### GET `/api/agreements/{id}` - UPDATED

**New Response Fields:**
```typescript
{
  // ... existing fields ...
  
  base_agreement_id: string | null;
  owner_name: string | null;
  tenant_name: string | null;    // Auto-filled after invite acceptance
  base_agreement: {
    id: string;
    title: string;
    version: string;
    city_name: string;
    state_name: string;
    country_name: string;
  } | null;
}
```

---

### PATCH `/api/agreements/{id}` - UPDATED

**New Request Fields:**
```typescript
{
  // ... existing fields ...
  base_agreement_id?: string;
  owner_name?: string;
}
```

---

## TypeScript Interfaces

Add to `types/index.ts`:

```typescript
// ==================== LOCATIONS ====================

export interface Country {
  id: string;
  code: string;
  name: string;
}

export interface State {
  id: string;
  country_id: string;
  code: string | null;
  name: string;
}

export interface City {
  id: string;
  state_id: string;
  name: string;
}

// ==================== BASE AGREEMENT ====================

export interface BaseAgreement {
  id: string;
  city_id: string;
  city_name: string;
  state_name: string;
  country_name: string;
  title: string;
  version: string;
  content: string | null;
  applicable_for: 'landlord' | 'tenant' | 'both';
  is_active: boolean;
  effective_date: string | null;
  created_at: string;
}

export interface BaseAgreementSummary {
  id: string;
  title: string;
  version: string;
  city_name?: string;
  state_name?: string;
  country_name?: string;
}

export interface BaseAgreementCreate {
  city_id: string;
  title: string;
  version?: string;
  content?: string;
  applicable_for?: 'landlord' | 'tenant' | 'both';
  effective_date?: string;
}

export interface BaseAgreementUpdate {
  title?: string;
  version?: string;
  content?: string;
  applicable_for?: string;
  is_active?: boolean;
  effective_date?: string;
}

// ==================== UPDATED AGREEMENT ====================

// Update existing AgreementCreate
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
  base_agreement_id?: string;    // NEW
  owner_name?: string;           // NEW
  terms?: AgreementTerms;
  parties?: AgreementPartyCreate[];
}

// Update existing AgreementResponse
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
  base_agreement_id: string | null;     // NEW
  owner_name: string | null;            // NEW
  tenant_name: string | null;           // NEW
  base_agreement: BaseAgreementSummary | null;  // NEW
  terms: AgreementTerms | null;
  parties: AgreementParty[];
}
```

---

## Service Files

### File: `services/locationService.ts`

```typescript
import { api } from './api';
import { Country, State, City, BaseAgreement, BaseAgreementSummary } from '@/types';

export const locationService = {
  // ========== COUNTRIES ==========
  getCountries: () => 
    api.get<Country[]>('/api/locations/countries', false),  // No auth

  getCountry: (id: string) =>
    api.get<Country>(`/api/locations/countries/${id}`, false),

  // ========== STATES ==========
  getStates: (countryId: string) => 
    api.get<State[]>(`/api/locations/countries/${countryId}/states`, false),

  getState: (id: string) =>
    api.get<State>(`/api/locations/states/${id}`, false),

  // ========== CITIES ==========
  getCities: (stateId: string) => 
    api.get<City[]>(`/api/locations/states/${stateId}/cities`, false),

  getCity: (id: string) =>
    api.get<City>(`/api/locations/cities/${id}`, false),
};
```

---

### File: `services/baseAgreementService.ts`

```typescript
import { api } from './api';
import { 
  BaseAgreement, 
  BaseAgreementSummary, 
  BaseAgreementCreate, 
  BaseAgreementUpdate 
} from '@/types';

export const baseAgreementService = {
  // Get base agreement for a city (public)
  getByCity: (cityId: string) => 
    api.get<BaseAgreement>(`/api/base-agreements/city/${cityId}`, false),

  // Get by ID
  get: (id: string) => 
    api.get<BaseAgreement>(`/api/base-agreements/${id}`),

  // List all (admin)
  list: (params?: { city_id?: string; is_active?: boolean }) => {
    const query = new URLSearchParams();
    if (params?.city_id) query.append('city_id', params.city_id);
    if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));
    return api.get<BaseAgreementSummary[]>(`/api/base-agreements?${query}`);
  },

  // Create (admin)
  create: (data: BaseAgreementCreate) => 
    api.post<BaseAgreement>('/api/base-agreements', data),

  // Update (admin)
  update: (id: string, data: BaseAgreementUpdate) => 
    api.patch<BaseAgreement>(`/api/base-agreements/${id}`, data),

  // Delete (admin)
  delete: (id: string) => 
    api.delete<void>(`/api/base-agreements/${id}`),

  // Activate/Deactivate (admin)
  activate: (id: string) => 
    api.post<BaseAgreement>(`/api/base-agreements/${id}/activate`, {}),

  deactivate: (id: string) => 
    api.post<BaseAgreement>(`/api/base-agreements/${id}/deactivate`, {}),
};
```

---

## Updated User Flow

### New Agreement Creation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: SELECT LOCATION                                        │
├─────────────────────────────────────────────────────────────────┤
│  Country:  [United States          ▼]                          │
│  State:    [California             ▼]  ← loads after country   │
│  City:     [Los Angeles            ▼]  ← loads after state     │
│                                                                 │
│  [Load Base Agreement →]                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: REVIEW BASE AGREEMENT                                   │
├─────────────────────────────────────────────────────────────────┤
│  📄 Los Angeles Roommate Agreement v1.0.0                      │
│  ─────────────────────────────────────────────────────────────  │
│  [Scrollable preview of 20-30 page agreement]                   │
│                                                                 │
│  ☑ I have read and agree to the base agreement terms           │
│                                                                 │
│  [← Back]                              [Continue to Details →]  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: ENTER DETAILS                                           │
├─────────────────────────────────────────────────────────────────┤
│  Owner/Landlord Name: [John Smith                    ]          │
│                                                                 │
│  Property Address                                               │
│  Address Line 1:      [123 Main Street               ]          │
│  Address Line 2:      [Apt 4B                        ]          │
│  City:                Los Angeles  (auto-filled)                │
│  State:               California   (auto-filled)                │
│  Postal Code:         [90001                         ]          │
│  Country:             United States (auto-filled)               │
│                                                                 │
│  Total Monthly Rent:  [$2,500.00                     ]          │
│  Start Date:          [2024-02-01                    ]          │
│  End Date:            [2025-01-31                    ]          │
│                                                                 │
│  [← Back]                              [Create Agreement →]     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
              POST /api/agreements
              {
                base_agreement_id: "...",
                owner_name: "John Smith",
                address_line1: "123 Main Street",
                city: "Los Angeles",
                state: "California",
                country: "United States",
                rent_total_cents: 250000,
                ...
              }
                              ↓
         (Continue with existing flow: finalize → pay → invite → sign)
```

---

## UI Components

### Component: `LocationSelector.tsx`

```tsx
'use client';

import { useState, useEffect } from 'react';
import { locationService } from '@/services/locationService';
import { baseAgreementService } from '@/services/baseAgreementService';
import { Country, State, City, BaseAgreement } from '@/types';
import { Loader2 } from 'lucide-react';

interface LocationSelectorProps {
  onBaseAgreementLoaded: (agreement: BaseAgreement, location: {
    country: Country;
    state: State;
    city: City;
  }) => void;
}

export function LocationSelector({ onBaseAgreementLoaded }: LocationSelectorProps) {
  // Data
  const [countries, setCountries] = useState<Country[]>([]);
  const [states, setStates] = useState<State[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  
  // Selected values
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null);
  const [selectedState, setSelectedState] = useState<State | null>(null);
  const [selectedCity, setSelectedCity] = useState<City | null>(null);
  
  // Loading states
  const [loadingCountries, setLoadingCountries] = useState(true);
  const [loadingStates, setLoadingStates] = useState(false);
  const [loadingCities, setLoadingCities] = useState(false);
  const [loadingAgreement, setLoadingAgreement] = useState(false);
  
  // Error
  const [error, setError] = useState<string | null>(null);

  // Load countries on mount
  useEffect(() => {
    locationService.getCountries()
      .then(setCountries)
      .catch(() => setError('Failed to load countries'))
      .finally(() => setLoadingCountries(false));
  }, []);

  // Load states when country changes
  const handleCountryChange = async (country: Country) => {
    setSelectedCountry(country);
    setSelectedState(null);
    setSelectedCity(null);
    setStates([]);
    setCities([]);
    setError(null);
    
    setLoadingStates(true);
    try {
      const statesData = await locationService.getStates(country.id);
      setStates(statesData);
    } catch {
      setError('Failed to load states');
    } finally {
      setLoadingStates(false);
    }
  };

  // Load cities when state changes
  const handleStateChange = async (state: State) => {
    setSelectedState(state);
    setSelectedCity(null);
    setCities([]);
    setError(null);
    
    setLoadingCities(true);
    try {
      const citiesData = await locationService.getCities(state.id);
      setCities(citiesData);
    } catch {
      setError('Failed to load cities');
    } finally {
      setLoadingCities(false);
    }
  };

  // Load base agreement when city selected and button clicked
  const handleLoadAgreement = async () => {
    if (!selectedCity || !selectedState || !selectedCountry) return;
    
    setError(null);
    setLoadingAgreement(true);
    
    try {
      const agreement = await baseAgreementService.getByCity(selectedCity.id);
      onBaseAgreementLoaded(agreement, {
        country: selectedCountry,
        state: selectedState,
        city: selectedCity,
      });
    } catch (err: any) {
      if (err.status === 404) {
        setError(`No agreement template available for ${selectedCity.name} yet.`);
      } else {
        setError('Failed to load agreement template');
      }
    } finally {
      setLoadingAgreement(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Select Your Location</h2>
      
      {/* Country Dropdown */}
      <div>
        <label className="block text-sm font-medium mb-2">Country</label>
        <select
          className="w-full p-3 border rounded-lg"
          value={selectedCountry?.id || ''}
          onChange={(e) => {
            const country = countries.find(c => c.id === e.target.value);
            if (country) handleCountryChange(country);
          }}
          disabled={loadingCountries}
        >
          <option value="">Select a country</option>
          {countries.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* State Dropdown */}
      <div>
        <label className="block text-sm font-medium mb-2">State / Province</label>
        <select
          className="w-full p-3 border rounded-lg"
          value={selectedState?.id || ''}
          onChange={(e) => {
            const state = states.find(s => s.id === e.target.value);
            if (state) handleStateChange(state);
          }}
          disabled={!selectedCountry || loadingStates}
        >
          <option value="">{loadingStates ? 'Loading...' : 'Select a state'}</option>
          {states.map(s => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </div>

      {/* City Dropdown */}
      <div>
        <label className="block text-sm font-medium mb-2">City</label>
        <select
          className="w-full p-3 border rounded-lg"
          value={selectedCity?.id || ''}
          onChange={(e) => {
            const city = cities.find(c => c.id === e.target.value);
            if (city) setSelectedCity(city);
          }}
          disabled={!selectedState || loadingCities}
        >
          <option value="">{loadingCities ? 'Loading...' : 'Select a city'}</option>
          {cities.map(c => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error}
        </div>
      )}

      {/* Load Agreement Button */}
      <button
        onClick={handleLoadAgreement}
        disabled={!selectedCity || loadingAgreement}
        className="w-full py-3 px-6 bg-blue-600 text-white rounded-lg font-medium
                   disabled:bg-gray-300 disabled:cursor-not-allowed
                   hover:bg-blue-700 transition-colors"
      >
        {loadingAgreement ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="animate-spin h-5 w-5" />
            Loading Agreement...
          </span>
        ) : (
          'Load Base Agreement'
        )}
      </button>
    </div>
  );
}
```

---

## Sample API Responses

### Countries (26 total)

```json
[
  { "id": "31d12bc2-3491-4fff-9a08-8adebc7f7f28", "code": "AU", "name": "Australia" },
  { "id": "e1a806fb-e834-48b5-8c46-54ee8a2f370f", "code": "BD", "name": "Bangladesh" },
  { "id": "66c25c71-9262-4173-97b4-3ac6c5f92e56", "code": "BR", "name": "Brazil" },
  { "id": "645908a6-4a7a-4857-8f08-686eb01214b5", "code": "CA", "name": "Canada" },
  { "id": "7f1875d1-e90f-46af-809d-953527e6b2e7", "code": "CN", "name": "China" },
  { "id": "28ce4960-f950-454a-84b4-c1c2e919bab3", "code": "US", "name": "United States" }
]
```

### US States (51 total)

```json
[
  { "id": "17f1c875-c9e8-4e88-b2ca-a741b2344ade", "country_id": "28ce4960-...", "code": "AL", "name": "Alabama" },
  { "id": "828ef706-cd22-4d04-96a6-bcf5dbf24e17", "country_id": "28ce4960-...", "code": "CA", "name": "California" },
  { "id": "904d9ed8-d95d-4d46-bb2c-28c61425eee2", "country_id": "28ce4960-...", "code": "NY", "name": "New York" }
]
```

### California Cities (14 total)

```json
[
  { "id": "7adb0e45-10c7-45d8-a11b-27a089e34f11", "state_id": "828ef706-...", "name": "Los Angeles" },
  { "id": "c9c38f7b-bb0f-49c5-a797-73800b1eb14d", "state_id": "828ef706-...", "name": "San Francisco" },
  { "id": "06ccec4f-bc9f-485a-89f8-759367677b87", "state_id": "828ef706-...", "name": "San Jose" }
]
```

---

## Backend Quick Reference

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/locations/countries` | GET | No | List all countries |
| `/api/locations/countries/{id}` | GET | No | Get single country |
| `/api/locations/countries/{id}/states` | GET | No | Get states for country |
| `/api/locations/states/{id}` | GET | No | Get single state |
| `/api/locations/states/{id}/cities` | GET | No | Get cities for state |
| `/api/locations/cities/{id}` | GET | No | Get single city |
| `/api/base-agreements/city/{city_id}` | GET | No | Get base agreement for city |
| `/api/base-agreements` | GET | Yes | List all base agreements |
| `/api/base-agreements` | POST | Yes | Create base agreement |
| `/api/base-agreements/{id}` | GET | Yes | Get base agreement |
| `/api/base-agreements/{id}` | PATCH | Yes | Update base agreement |
| `/api/base-agreements/{id}` | DELETE | Yes | Delete base agreement |
| `/api/base-agreements/{id}/activate` | POST | Yes | Activate |
| `/api/base-agreements/{id}/deactivate` | POST | Yes | Deactivate |
| `/api/base-agreements/{id}/pdf/upload-sas` | POST | Yes | Get PDF upload URL |
| `/api/base-agreements/{id}/pdf` | POST | Yes | Attach PDF after upload |
| `/api/base-agreements/{id}/pdf` | DELETE | Yes | Remove PDF |
| `/api/base-agreements/{id}/pdf/download-sas` | GET | No | Get PDF download URL |

---

## Implementation Checklist for Frontend

1. **Add TypeScript types** in `types/index.ts`
2. **Create `locationService.ts`** in `services/`
3. **Create `baseAgreementService.ts`** in `services/`
4. **Create `LocationSelector` component**
5. **Create `AgreementPreview` component** for displaying base agreement content or PDF
6. **Create `PdfUploader` component** for admin to upload PDF files
7. **Create `PdfViewer` component** to display/download PDF agreements
8. **Update agreement creation form** to include location step first
9. **Update `agreementService.create()`** to include `base_agreement_id` and `owner_name`
10. **Update agreement display pages** to show linked base agreement info

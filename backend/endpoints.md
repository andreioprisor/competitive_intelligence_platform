# API Endpoints Documentation

## 1. GET /COMPANY_PROFILE

**Description:** Retrieve company profile information

**Features:**

- Caching enabled

**Parameters:**

- `COMPANY_DOMAIN` (string): The domain of the company

**Response:**

- `COMPANY_PROFILE` (JSON): The company profile data
- Cache hit indicator: Boolean indicating whether the result was retrieved from cache

---

## 2. UPDATE /COMPANY_PROFILE

**Description:** Update company profile information

**Features:**

- Caching enabled

**Parameters:**

- `COMPANY_PROFILE` (JSON): The updated company profile data

**Response:**

- None

---

## 3. GET /SOLUTIONS

**Description:** Retrieve a list of solutions for a company

**Parameters:**

- `COMPANY_DOMAIN` (string): The domain of the company

**Response:**

- List of solutions (JSON): Array of solutions offered by the company

---

## 4. UPDATE /SOLUTIONS

**Description:** Update a solution for a company

**Parameters:**

- `COMPANY_DOMAIN` (string): The domain of the company
- `SOLUTION` (JSON): The solution data to update

**Response:**

- None

---

## 5. GET /COMPETITORS

**Description:** Retrieve a list of competitors for a company

**Parameters:**

- `COMPANY_DOMAIN` (string): The domain of the company

**Response:**

- List of competitors (JSON): Array of competitor information

---

## 6. POST /COMPETITORS

**Description:** Add a new competitor for a company

**Parameters:**

- `COMPANY_DOMAIN` (string): The domain of the company
- `COMPETITOR` (JSON): The competitor data to add

**Response:**

- None

---

## 7. POST /CATEGORY_OBSERVED

**Description:** Record a category observation for a company

**Parameters:**

- `COMPANY_DOMAIN` (string): The domain of the company
- `CATEGORY_LABEL` (string): The label/name of the category
- `DESCRIPTION` (text): Detailed description of the observation

**Behavior:**

- Inserts the category observation into the database

**Response:**

- The created category observation (JSON)

---

## 8. GET /SOLUTIONS_COMPARISON

**Description:** Compare solutions between a company and its competitor

**Parameters:**

- `COMPANY_DOMAIN` (string): The domain of the company
- `COMPANY_SOLUTION` (JSON): The company's solution data
- `COMPETITOR_SOLUTION` (JSON): The competitor's solution data

**Response:**

- Comparison result (text): Detailed comparison analysis

---

## 9. GET /NOTIFICATIONS

**Description:** Retrieve notifications about competitors

**Parameters:**

- `COMPANY_DOMAIN` (string): The domain of the company
- `COMPETITOR` (JSON): The competitor data
- `CHANNEL` (string): The notification channel

**Response:**

- List of notifications (JSON): Array of notification objects

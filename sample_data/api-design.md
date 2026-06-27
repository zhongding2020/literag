# Microservices API Design Guide

## Overview
This document describes the API design standards for our microservices architecture.

## REST API Standards
- Base URL: `/api/v1`
- Authentication: JWT Bearer tokens
- Rate limiting: 1000 requests/minute per client

## Endpoints

### User Service
| Method | Path | Description |
|--------|------|-------------|
| GET | /users | List all users |
| POST | /users | Create new user |
| GET | /users/{id} | Get user details |
| PUT | /users/{id} | Update user |
| DELETE | /users/{id} | Delete user |

### Product Service
| Method | Path | Description |
|--------|------|-------------|
| GET | /products | List products |
| POST | /products | Create product |
| GET | /products/{id} | Get product details |
| PUT | /products/{id} | Update product |

## Error Handling
All errors return RFC 7807 Problem Details format:
```json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request body contains invalid fields.",
  "instance": "/api/v1/users"
}
```

## Pagination
All list endpoints support cursor-based pagination:
- `cursor`: Opaque cursor for the next page
- `limit`: Maximum items per page (default: 20, max: 100)

## Versioning
API versions are indicated via the URL path prefix (v1, v2).
Breaking changes require a new version number.

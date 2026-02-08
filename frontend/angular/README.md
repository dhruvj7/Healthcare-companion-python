# Healthcare Companion - Angular Frontend

## Setup Instructions

### Prerequisites
- Node.js (v18 or higher)
- Angular CLI (`npm install -g @angular/cli`)

### Installation

```bash
# Create new Angular project
ng new healthcare-companion-ui
cd healthcare-companion-ui

# Install dependencies
npm install

# Start development server
ng serve

# Open browser
# Navigate to http://localhost:4200
```

### Project Structure

```
healthcare-companion-ui/
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── chat.component.ts
│   │   │   │   ├── chat.component.html
│   │   │   │   └── chat.component.css
│   │   │   └── capabilities/
│   │   │       ├── capabilities.component.ts
│   │   │       ├── capabilities.component.html
│   │   │       └── capabilities.component.css
│   │   ├── services/
│   │   │   └── chat.service.ts
│   │   ├── models/
│   │   │   └── chat.models.ts
│   │   ├── app.component.ts
│   │   ├── app.component.html
│   │   └── app.component.css
│   ├── environments/
│   │   ├── environment.ts
│   │   └── environment.prod.ts
│   └── styles.css
```

## Configuration

Update `src/environments/environment.ts`:

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1'
};
```

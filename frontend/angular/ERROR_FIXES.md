# Common Angular Compile Errors - Quick Fixes

## 🔍 Run This First

```bash
cd frontend/angular
diagnose.bat    # Windows
```

This will tell you exactly what's wrong.

---

## Error 1: "Cannot find module @angular/..."

**Error Message:**
```
Error: Cannot find module '@angular/core'
Error: Cannot find module '@angular/common'
```

**Fix:**
```bash
rm -rf node_modules package-lock.json
npm install
```

**If that fails:**
```bash
npm install --legacy-peer-deps
```

---

## Error 2: "NG0303: Can't bind to 'ngForOf'"

**Error Message:**
```
Can't bind to 'ngForOf' since it isn't a known property
Can't bind to 'ngIf' since it isn't a known property
```

**Fix:** Already fixed in `app.module.ts` - make sure CommonModule is imported:

```typescript
import { CommonModule } from '@angular/common';

@NgModule({
  imports: [
    BrowserModule,
    CommonModule,  // ← This line is required!
    HttpClientModule,
    FormsModule
  ]
})
```

---

## Error 3: "The pipe 'safeHtml' could not be found"

**Error Message:**
```
The pipe 'safeHtml' could not be found
NG8004: No pipe found with name 'safeHtml'
```

**Fix:** Make sure `SafeHtmlPipe` is declared in app.module.ts:

```typescript
import { SafeHtmlPipe } from './pipes/safe-html.pipe';

@NgModule({
  declarations: [
    AppComponent,
    ChatComponent,
    SafeHtmlPipe  // ← Must be here!
  ]
})
```

**Also verify the file exists:**
```bash
# Check if file exists
ls src/app/pipes/safe-html.pipe.ts
```

---

## Error 4: "Type 'string' is not assignable to type 'SafeHtml'"

**Error Message:**
```
Type 'string' is not assignable to type 'SafeHtml'
```

**Already Fixed!** The SafeHtmlPipe now uses `bypassSecurityTrustHtml()` correctly.

---

## Error 5: Component not found

**Error Message:**
```
'app-chat' is not a known element
Component 'ChatComponent' is not included in a module
```

**Fix:** Verify ChatComponent is in declarations:

```typescript
@NgModule({
  declarations: [
    AppComponent,
    ChatComponent,  // ← Must be here!
    SafeHtmlPipe
  ]
})
```

---

## Error 6: HttpClient errors

**Error Message:**
```
NullInjectorError: No provider for HttpClient
```

**Fix:** Already included in app.module.ts:

```typescript
import { HttpClientModule } from '@angular/common/http';

@NgModule({
  imports: [
    HttpClientModule  // ← Required for API calls
  ]
})
```

---

## Error 7: FormsModule errors

**Error Message:**
```
Can't bind to 'ngModel' since it isn't a known property
```

**Fix:** Already included:

```typescript
import { FormsModule } from '@angular/forms';

@NgModule({
  imports: [
    FormsModule  // ← Required for [(ngModel)]
  ]
})
```

---

## Error 8: Port already in use

**Error Message:**
```
Port 4200 is already in use
```

**Fix:**
```bash
# Option 1: Use different port
ng serve --port 4201

# Option 2: Kill process on port 4200 (Windows)
netstat -ano | findstr :4200
taskkill /PID <PID> /F
```

---

## Error 9: TypeScript compilation errors

**Error Message:**
```
TS2304: Cannot find name...
TS2339: Property does not exist...
```

**Fix:**
```bash
# Clean TypeScript cache
rm -rf dist
rm -rf .angular

# Rebuild
ng serve
```

---

## Error 10: Environment file missing

**Error Message:**
```
Cannot find module './environments/environment'
```

**Fix:** Create the file:

```typescript
// src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1'
};
```

---

## Complete Reset (Nuclear Option)

If nothing else works:

```bash
# 1. Backup your files
mkdir backup
copy src\app\components backup\components /E
copy src\app\services backup\services /E
copy src\app\models backup\models /E
copy src\app\pipes backup\pipes /E

# 2. Clean everything
rm -rf node_modules
rm -rf package-lock.json
rm -rf dist
rm -rf .angular

# 3. Reinstall
npm install --legacy-peer-deps

# 4. Try to compile
ng serve
```

---

## Check Your Files Match These Exactly

### src/app/app.module.ts
```typescript
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

import { AppComponent } from './app.component';
import { ChatComponent } from './components/chat/chat.component';
import { SafeHtmlPipe } from './pipes/safe-html.pipe';

@NgModule({
  declarations: [
    AppComponent,
    ChatComponent,
    SafeHtmlPipe
  ],
  imports: [
    BrowserModule,
    CommonModule,
    HttpClientModule,
    FormsModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

### src/app/pipes/safe-html.pipe.ts
```typescript
import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Pipe({
  name: 'safeHtml'
})
export class SafeHtmlPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(value: string): SafeHtml {
    if (!value) {
      return '';
    }

    let formatted = value
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/_(.+?)_/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/^\* (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>');

    return this.sanitizer.bypassSecurityTrustHtml(formatted);
  }
}
```

---

## Still Getting Errors?

### Step 1: Copy the exact error message

### Step 2: Check if it matches above

### Step 3: Try these commands in order:

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install

# If error persists
npm install --legacy-peer-deps

# If still error
npm cache clean --force
npm install

# Last resort
ng serve --poll=2000
```

---

## Verify Backend is Running

Many "errors" are actually backend connection issues:

```bash
# Test backend
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","service":"symptom-analysis"}
```

---

## Get Detailed Error Info

```bash
# Run with verbose logging
ng serve --verbose

# Check for TypeScript errors
ng build

# Run in production mode to see different errors
ng serve --configuration production
```

---

## Common File Issues

**Make sure these folders/files exist:**

```
src/
├── app/
│   ├── components/
│   │   └── chat/
│   │       ├── chat.component.ts
│   │       ├── chat.component.html
│   │       └── chat.component.css
│   ├── services/
│   │   └── chat.service.ts
│   ├── models/
│   │   └── chat.models.ts
│   ├── pipes/
│   │   └── safe-html.pipe.ts
│   ├── app.module.ts
│   ├── app.component.ts
│   ├── app.component.html
│   └── app.component.css
├── environments/
│   └── environment.ts
└── styles.css
```

---

## Quick Test

After fixing, test that everything works:

```bash
# 1. Start server
ng serve

# 2. Open browser
http://localhost:4200

# 3. Check console (F12)
# Should have NO red errors

# 4. Type test message
"I have a fever"

# 5. Should see response
# With intent badge
```

---

## Need More Help?

Run the diagnostic script:
```bash
diagnose.bat
```

This will check:
- ✅ Node.js installed
- ✅ npm installed
- ✅ Angular CLI installed
- ✅ All required files present
- ✅ node_modules exists

Then tell me the EXACT error message you see!

# Frontend Setup - Fixed Version

## Quick Setup (3 Steps)

### Step 1: Install Dependencies

```bash
cd frontend/angular
npm install
```

If you get any peer dependency warnings, run:
```bash
npm install --legacy-peer-deps
```

### Step 2: Verify Project Structure

Make sure these files exist:
- ✅ `src/app/app.module.ts`
- ✅ `src/app/components/chat/chat.component.ts`
- ✅ `src/app/services/chat.service.ts`
- ✅ `src/app/models/chat.models.ts`
- ✅ `src/app/pipes/safe-html.pipe.ts`
- ✅ `src/environments/environment.ts`

### Step 3: Start the Server

```bash
ng serve
```

Or if `ng` is not found:
```bash
npm start
```

**UI will be available at:** `http://localhost:4200`

---

## Common Errors & Fixes

### Error: "Cannot find module '@angular/core'"

**Fix:**
```bash
rm -rf node_modules package-lock.json
npm install
```

### Error: "ng: command not found"

**Fix:**
```bash
npm install -g @angular/cli
```

Or use npm scripts instead:
```bash
npm start
```

### Error: "Port 4200 is already in use"

**Fix:**
```bash
ng serve --port 4201
```

### Error: Cannot find module 'ngx-markdown'

**Fix:** Already removed! Just run:
```bash
npm install
```

### Error: Module has no exported member

**Fix:** Make sure all imports in `app.module.ts` are correct:
```typescript
import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
```

---

## Verify Backend is Running

Before testing the frontend, make sure backend is running:

```bash
# In a separate terminal
cd ../..
uvicorn app.main:app --reload
```

Backend should be at: `http://localhost:8000`

---

## Test the Application

1. **Open Browser:** `http://localhost:4200`

2. **You should see:**
   - Healthcare Companion header
   - Welcome message from AI
   - Example prompt buttons
   - Input field at the bottom

3. **Try typing:**
   - "I have a fever"
   - Click Send
   - Watch the AI respond!

---

## Project Structure

```
frontend/angular/
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   └── chat/
│   │   │       ├── chat.component.ts     ✅ Main component
│   │   │       ├── chat.component.html   ✅ Template
│   │   │       └── chat.component.css    ✅ Styles
│   │   ├── services/
│   │   │   └── chat.service.ts           ✅ API service
│   │   ├── models/
│   │   │   └── chat.models.ts            ✅ TypeScript types
│   │   ├── pipes/
│   │   │   └── safe-html.pipe.ts         ✅ HTML formatter
│   │   ├── app.module.ts                 ✅ Main module
│   │   ├── app.component.ts
│   │   ├── app.component.html
│   │   └── app.component.css
│   ├── environments/
│   │   └── environment.ts                ✅ Config
│   └── styles.css                        ✅ Global styles
├── angular.json                          ✅ Angular config
├── package.json                          ✅ Dependencies
└── tsconfig.json                         ✅ TypeScript config
```

---

## Update API URL (if needed)

If your backend is running on a different port, update:

**File:** `src/environments/environment.ts`

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1'  // Change port if needed
};
```

---

## Troubleshooting Checklist

- [ ] Node.js installed? (`node --version`)
- [ ] npm installed? (`npm --version`)
- [ ] In correct directory? (`cd frontend/angular`)
- [ ] Dependencies installed? (`npm install`)
- [ ] Backend running? (`curl http://localhost:8000/health`)
- [ ] Port 4200 available? (Close other Angular apps)

---

## Still Having Issues?

1. **Clear everything and start fresh:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ng serve
   ```

2. **Check backend logs** for CORS errors

3. **Check browser console** (F12) for errors

4. **Try a different browser** (Chrome recommended)

---

## Success! 🎉

When it works, you should see:
- ✅ UI loads without errors
- ✅ Welcome message displays
- ✅ Can type messages
- ✅ AI responds to your messages
- ✅ Intent badges show up
- ✅ No errors in browser console

---

**Ready to go! Type "I have a fever" to test!** 🚀

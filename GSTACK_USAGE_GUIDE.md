# 📘 دليل استخدام gstack في مشروع AgeixAISOC

## المتطلبات المثبتة (تم بالفعل)
- ✅ **Claude Code** extension في VS Code (`anthropic.claude-code`)
- ✅ **gstack** مثبت في `C:\Users\Digilians\.claude\skills\gstack`
- ✅ **كل الـ 55 skill** مرتبطة (review, qa, cso, ship, ...)
- ✅ **CLAUDE.md** يحتوي سياق مشروعك + قسم gstack

---

## 🟢 طريقة الاستخدام — خطوة بخطوة

### 1️⃣ افتح Claude Code في VS Code
```
افتح VS Code على مشروع c:\Users\Digilians\Desktop\AgeixAISOC
ثم اضغط:  Ctrl + Shift + P
واكتب:    Claude Code: Open in New Terminal  (أو ابحث عن "Claude")
```
أو من الشريط الجانبي الأيسر اضغط أيقونة Claude (شعار الـ sparkle).

### 2️⃣ اكتب الأمر بأي من طريقتين

| الطريقة | مثال |
|---------|------|
| **Slash command** | `/review` |
| **وصف طبيعي** | "اعمل مراجعة أمنية للمشروع" |

---

## 🧠 أشهر الأوامر لمشروعك

| الأمر | ماذا يفعل | مثال للاستخدام |
|-------|-----------|----------------|
| `/office-hours` | يجلس معك مكتبياً ويعيد صياغة فكرتك قبل البرمجة | `/office-hours` ← صف لي Feature جديد |
| `/autoplan` | خطة كاملة (CEO → Design → Eng) | `/autoplan` |
| `/plan-eng-review` | مراجعة البنية التقنية للخطة | `/plan-eng-review` |
| `/review` | مراجعة الكود قبل الـ merge — يكتشف أخطاء CI لا تراها | `/review` |
| `/cso` | فحص أمني OWASP + STRIDE كامل | `/cso` |
| `/investigate` | يجب سبب خطأ لاغوف لا يهدّأ | "هذا الخلل ..." |
| `/ship` | تشغيل الاختبارات وعمل Push وفتح PR | `/ship` |
| `/qa` | اختبار ديناميكي عبر متصفح حقيقي | `/qa http://localhost:5173` |
| `/retro` | مراجعة الأسبوع الماضي | `/retro` |
| `/office-hours` | بداية مشروع جديد | `/office-hours` |

---

## 🎬 مثال عملي (مراقبة الكود)

```
أنت:  /review
Claude Code: [يغوص في الفرق، يحدد الأخطاء، ويقترح إصلاحات]
أنت:  موافق على الإصلاحات
Claude Code: يعمل الـ fixes تلقائياً + يوسّع الاختبارات
```

---

## ⚡ نصائح سريعة

- أول استخدام لكل skill يستغرق ~30 ثانية (update check) — طبيعي.
- إذا لم تظهر الأوامر، **أعد تشغيل نافذة VS Code** بعد السيت أب.
- إذا لاحظت أن Cloud Code يستخدم متصفحاً آخر، استخدم `/browse` — فهو الأبواب.
- كل مهارة تنتج مخرجات تغذي التالية (مثلاً `/office-hours` يكتب تصميماً تقرؤه `/plan`).

## ❗ ملاحظة
- أمر `/qa` وأمر `/browse` يحتاجون تحميل Chromium (~192MB) في أول مرة:
```
bash -lc "export PATH=\"$HOME/.bun/bin:$PATH\" && cd ~/.claude/skills/gstack && ./setup"
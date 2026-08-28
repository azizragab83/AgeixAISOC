# ⚡ تشغيل gstack Skills — برومبتات جاهزة للنسخ واللصق

> عند فتح Claude Code في VS Code، اكتب أي سطر من اللي تحت **كما هو** واضغط Enter. Claude Code هيتعرف على الـ skill ويشغّله.

---

## 🟢 أول ما تفتح Claude Code

افتح VS Code على مشروعك، ثم افتح Claude Code (أيقونة Claude في الشريط الجانبي).
**اكتب أول سطر:**
```
/office-hours
```
ده بيعلّم Claude Code إنك جاي تستخدم gstack، وبيجهّز السياق.

---

## 🎯 تشغيل Skill واحد — اكتب السطر ده

| Skill | اكتب بالظبط |
|-------|-------------|
| مراجعة الكود | `/review` |
| فحص أمني | `/cso` |
| تصحيح خطأ | `/investigate` |
| اختبار المتصفح | `/qa http://localhost:5173` |
| خطة كاملة | `/autoplan` |
| نشر | `/ship` |
| مراجعة أسبوعية | `/retro` |
| رأي OpenAI ثاني | `/codex` |
| توثيق | `/document-release` |
| رسم مخطط | `/diagram` |
| PDF | `/make-pdf` |
| قفل مجلد | `/freeze backend` |
| فك القفل | `/unfreeze` |

---

## 🚀 تشغيل كل الـ Skills دفعة واحدة — 3 طرق

### الطريقة 1: أمر واحد بيشغّل سلسلة كاملة
اكتب سطر واحد بس:
```
/autoplan
```
ده بيشغّل تلقائياً: **CEO review → Design review → Eng review** — كلهم في أمر واحد.

### الطريقة 2: سلسلة أوامر في برومبت واحد
انسخ ده كله في رسالة واحدة:
```
Load gstack. Run /office-hours, then /plan-ceo-review, then /plan-eng-review, then /review, then /cso, then /ship.
```
Claude Code هينفذهم بالترتيب واحد ورا التاني.

### الطريقة 3: برومبت كامل جاهز (الأقوى)
انسخ ده كله في رسالة واحدة:
```
Load gstack. Run the full pipeline on this project:
1. /office-hours — reframe what we're building
2. /plan-ceo-review — strategic review
3. /plan-eng-review — architecture review
4. /review — code review of current changes
5. /cso — full security audit (OWASP + STRIDE)
6. /ship — run tests, push, open PR
```
Claude Code هينفذ الـ 6 خطوات بالترتيب.

---

## 🧪 برومبتات جاهزة لمشروعك (SOC)

### فحص أمني كامل
```
Load gstack. Run /cso on this SOC platform. Focus on the FastAPI backend, API endpoints, and the orchestrator pipeline.
```

### مراجعة + نشر
```
Load gstack. Run /review on current changes, then /ship.
```

### تصحيح خطأ في الـ pipeline
```
Load gstack. Run /investigate. The LangGraph orchestrator pipeline is failing. Find the root cause.
```

### اختبار الداشبورد
```
Load gstack. Run /qa http://localhost:5173
```

### تخطيط feature جديد
```
Load gstack. Run /office-hours then /autoplan. I want to add a new SOAR playbook.
```

---

## 💡 ملاحظات مهمة

- **أول مرة** تشغّل أي skill بياخد ~30 ثانية (update check) — طبيعي.
- لو مش شايف الأوامر، **أعد تشغيل VS Code** مرة واحدة.
- `/autoplan` هو أسرع طريقة تشغّل 3 مراجعات في أمر واحد.
- كل skill بيغذّي اللي بعده (مثلاً `/office-hours` بيكتب تصميم يقرأه `/plan`).
- لو عايز تشغّل كل حاجة من غير ما تكتب حاجة، استخدم الطريقة 3 (البرومبت الكامل).
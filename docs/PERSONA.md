# Persona System (Abigael AI)

This document describes the Persona and PersonaVariant system for the Abigael companion.

Overview
- `Persona`: reusable persona templates that define tone, trait defaults, and voice preferences.
- `PersonaVariant`: persona-specific overrides to adjust phrasing, tone, or other traits.
- `CompanionProfile.selected_persona`: a user's chosen persona template.
- `CompanionProfile.selected_persona_variant`: a chosen variant (finer-grained override).

Admin
- Staff users can create and manage Personas and PersonaVariants via the admin UIs:
  - Personas: `/emotion_detection/personas/`
  - Variants: `/emotion_detection/personas/variants/`

Seeding
Run the development seed command to create sample personas and variants:

```bash
python manage.py seed_personas
```

Usage (User)
- Users can pick a persona at: `/emotion_detection/personas/select/`.
- When selecting a persona, active variants are loaded dynamically.
- The client preserves the selected variant in `localStorage` (key: `abigael_selected_variant_user_<user.id>`).

Integration
- The companion engine loads persona traits and applies them when generating messages.

Testing
- Run Django tests:

```bash
python manage.py test emotion_detection.tests.test_persona
```

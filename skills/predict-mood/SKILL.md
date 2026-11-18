---
name: predict-mood
description: Predict exactly six canonical moods from Spotify audio features, title semantics, and optional lyrics; use a Valence x Energy audio core with Romantic and Quirky audio fixed at 0, source-aware weighting, complete ranking, and percentages totaling 100%.
---

# Six-Mood Multimodal Classification Formula

Predict exactly six moods:

* Energetic
* Calm
* Romantic
* Dark
* Melancholy
* Quirky

Artist identity must NOT be used as a mood predictor.

## 1. Spotify Audio Core

Use Spotify's two strongest affect-related features directly:

```
V = valence
E = energy
```

Valence determines:

* High V: positive affect
* Low V: negative affect

Energy determines:

* High E: active / intense
* Low E: subdued / restrained

Do NOT construct a separate Arousal variable.

## 2. Core Audio Mood Scores

```
AUDIO_ENERGETIC  = V * E
AUDIO_CALM       = V * (1-E)
AUDIO_DARK       = (1-V) * E
AUDIO_MELANCHOLY = (1-V) * (1-E)
```

Core audio matrix:

| | Low Energy | High Energy |
| --- | --- | --- |
| High Valence | Calm | Energetic |
| Low Valence | Melancholy | Dark |

These four scores inherently satisfy:

```
AUDIO_ENERGETIC + AUDIO_CALM + AUDIO_DARK + AUDIO_MELANCHOLY = 1.0
```

Do not independently boost Dark or Melancholy using other Spotify features.

Dark and Melancholy share low Valence but compete on Energy.

Energetic and Calm share high Valence but compete on Energy.

## 3. Secondary Spotify Audio Features

Use these only as supporting evidence or confidence indicators:

* Danceability: high values may support Energetic.
* Tempo: high tempo may support Energetic/intensity; low tempo may support Calm/Melancholy.
* Loudness: high loudness may support intensity; low loudness may support subdued character.
* Mode: minor mode may weakly support negative affect; major mode may weakly support positive affect.
* Acousticness: may describe texture but is not direct emotional evidence.
* Instrumentalness: indicates likelihood of absence of vocals; do not treat as direct mood evidence.
* Speechiness: indicates spoken-word content; do not treat as direct mood evidence.
* Liveness: indicates likelihood of audience presence; do not treat as direct mood evidence.
* Time Signature: describes meter; do not treat unusual meter alone as Quirky.
* Key: do not use pitch class itself as a mood predictor.

IMPORTANT: Secondary features must NOT override the primary Valence x Energy classification.

## 4. Romantic and Quirky

Spotify Audio Features do not directly measure Romantic or Quirky.

Therefore:

```
AUDIO_ROMANTIC = 0
AUDIO_QUIRKY   = 0
```

Do NOT manufacture Romantic or Quirky scores from acousticness, instrumentalness, speechiness, time signature, or other Spotify features.

Romantic and Quirky are primarily semantic classifications determined from Title and Lyrics.

## 5. Title and Lyrics Semantic Scores

For Title and Lyrics independently, score all six moods from 0.00 to 1.00:

```
Energetic
Calm
Romantic
Dark
Melancholy
Quirky
```

Scale:

```
0.00 = no evidence
0.25 = weak evidence
0.50 = moderate evidence
0.75 = strong evidence
1.00 = explicit/dominant evidence
```

Interpret meaning contextually. Do NOT perform simple keyword matching.

### Energetic

Excitement, movement, action, celebration, confidence, urgency, power.

### Calm

Peace, serenity, comfort, rest, stillness, contemplation.

### Romantic

Love, intimacy, affection, attraction, devotion, romantic longing.

Generic positive language does NOT automatically mean Romantic.

### Dark

Threat, hostility, death, violence, fear, menace, danger, sinister imagery, obsession, aggression, psychological tension.

A hostile accusation, threat, or death-wish directed at a person (for example, telling someone they should have died instead) is explicit/dominant Dark evidence: score that source's `DARK` at 1.00 unless offsetting absurd, ironic, or genuinely playful context is present.

Hostile wording is Dark evidence. It is not Melancholy (no grief or longing) and not Quirky (no absurdity or playfulness).

### Melancholy

Sadness, grief, loss, regret, loneliness, heartbreak, nostalgia, wistfulness, reflective longing.

Negative language or references to death do NOT automatically mean Melancholy.

### Quirky

Absurdity, surrealism, irony, wordplay, eccentricity, unusual narrative, unexpected concepts, humorous incongruity, deliberate unconventionality.

Unexpected or unconventional wording is NOT automatically Quirky. It counts as Quirky evidence only when it is also absurd, ironic, playful, surreal, or wordplay.

```
Unexpected + hostile            -> Dark, not Quirky
Unexpected + grieving/sad       -> Melancholy, not Quirky
Unexpected + absurd/ironic/
             playful/surreal    -> Quirky evidence
```

Provocative, shocking, hostile, or dark language does NOT automatically mean Quirky. Without lyrics, a title alone often cannot establish absurdity, irony, or humor, so give strong Quirky scores only when the incongruity is clearly intentional and playful, not merely unusual.

## 6. Dark vs Melancholy Semantic Gate

For Title and Lyrics:

```
THREAT_INTENSITY   = hostility + menace + aggression + violence + psychological tension + sinister intent
REFLECTIVE_SADNESS = grief + sadness + regret + nostalgia + heartbreak + loneliness + longing
```

If THREAT_INTENSITY dominates: favor DARK.

If REFLECTIVE_SADNESS dominates: favor MELANCHOLY.

Precedence:

```
hostility + death wish              -> DARK (dominant), QUIRKY = 0.00
unexpected + absurd/ironic/playful/
             surreal                -> QUIRKY evidence
unexpected + hostile                -> DARK, not QUIRKY
```

Hostility, threat, violence, or a death-wish is Dark evidence even when the statement is also unexpected or unconventional. It does not become Melancholy without grief or longing, and does not become Quirky without absurdity or playfulness.

This semantic gate does NOT modify the Spotify audio calculation.

## 7. Multimodal Combination

When Audio, Title, and Lyrics are available:

For Energetic, Calm, Dark, and Melancholy:

```
RAW_M = 0.40*AUDIO_M + 0.40*TITLE_M + 0.20*LYRICS_M
```

For Romantic and Quirky, Audio contains no direct evidence, so redistribute the available semantic weights:

```
RAW_ROMANTIC = (0.40*TITLE_ROMANTIC + 0.20*LYRICS_ROMANTIC) / 0.60
RAW_QUIRKY   = (0.40*TITLE_QUIRKY   + 0.20*LYRICS_QUIRKY)   / 0.60
```

If Lyrics are unavailable:

For Energetic, Calm, Dark, Melancholy:

```
RAW_M = 0.50*AUDIO_M + 0.50*TITLE_M
```

For Romantic and Quirky:

```
RAW_M = TITLE_M
```

Missing evidence is UNKNOWN, not zero.

## 8. Final Normalization

After calculating all six RAW scores:

```
TOTAL = RAW_ENERGETIC + RAW_CALM + RAW_ROMANTIC + RAW_DARK + RAW_MELANCHOLY + RAW_QUIRKY
```

For every mood:

```
P_M = RAW_M / TOTAL
MOOD_PERCENTAGE = P_M * 100
```

The six final percentages must total exactly 100%.

## 9. Classification

```
Primary Mood   = highest normalized score
Secondary Mood = second-highest normalized score
```

If the top two scores differ by less than 3 percentage points, treat them as effectively co-dominant while retaining the mathematical ranking.

Confidence is separate from the six-mood distribution and should reflect:

* source completeness
* semantic ambiguity
* agreement between Audio, Title, and Lyrics

Do NOT use Artist identity as a mood predictor.

## 10. Required Output

Always output all six moods, sorted by normalized percentage from highest to lowest:

| Rank | Mood | Audio | Title | Lyrics | Raw Combined | Normalized % |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | ... | ... | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... | ... | ... |
| 3 | ... | ... | ... | ... | ... | ... |
| 4 | ... | ... | ... | ... | ... | ... |
| 5 | ... | ... | ... | ... | ... | ... |
| 6 | ... | ... | ... | ... | ... | ... |

For Romantic and Quirky, display `Audio = 0.0000`.

If Lyrics are unavailable, display `Lyrics = N/A`.

Never display unavailable evidence as zero.

Also report:

```
Primary Mood = Rank 1
Secondary Mood = Rank 2
Confidence = High / Medium / Low
```

If applicable, report that Rank 1 and Rank 2 are effectively co-dominant.

The six ranked normalized percentages must total exactly 100%.

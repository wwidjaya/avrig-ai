# Markdown <-> AML Bridge

Every entity lives twice in `.edm/`:

```text
domains/<domain>/<module>/entities/<Entity>.md      human-readable  (source of truth)
domains/<domain>/<module>/entities/<Entity>.aml     Azimutt AML     (derived)
```

**`<Entity>.md` is authoritative.** `.aml` is regenerated on every modify.
Never edit `.aml` by hand — edit `.md`, then re-run the modify/read path to sync.

## Column mapping

| Markdown table column | AML attribute token | Notes                        |
|-----------------------|---------------------|------------------------------|
| Column                | attribute name      | `Entity.aml` root anchor     |
| Type                  | type                | `varchar(256)`, `timestamp`  |
| PK                    | `pk`                |                              |
| Nullable              | `nullable`          | AML defaults to NOT NULL     |
| Default               | `=default`          | backtick expr: ``=`now()```  |
| Description           | (comment)           | kept in `.md` only           |

### Example

| Column | Type | PK | Nullable | Default | Description |
|--------|------|----|----------|---------|-------------|
| id | uuid | Yes |  |  | primary key |
| email | varchar(256) |  |  |  | |
| bio | text |  | Yes |  | |

becomes

```aml
Entity
  id uuid pk
  email varchar(256)
  bio text nullable
```

## Foreign key mapping

| Markdown FK row | AML token | Example                          |
|-----------------|-----------|----------------------------------|
| FK Name         | (inline)  | `<= col name`                    |
| Column          | `<= att`   | `order_id <= orders.id`          |
| Reference Entity | `<= target` | `orders(id)`                  |
| Reference Column | `<= (id)` |                                  |

```aml
orders
  id uuid pk
  user_id uuid <= users(id)
```

Note: parser stores FK by **column name**. A column may carry only one FK.

## Idempotence rule

- `add` writes both files.
- `modify` rewrites `.aml` from `.md`.
- `read` renders Markdown table from `.md` (never parses `.aml`).
- `move` relocates both files and re-keys `database`/`schema` from target indexes.
- `delete` removes both files.
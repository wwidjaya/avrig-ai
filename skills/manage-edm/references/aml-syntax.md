# AML (Azimutt Markup Language) Syntax Reference

Azimutt's minimal DSL for database schemas.

## Entities (Tables)

```aml
users
  id uuid pk
  email varchar(256) unique
  name varchar
  bio text nullable
  role varchar=guest
  created_at timestamp=`now()`
  profile_id uuid -> profiles(id)
```

## Attribute Options

- **pk**: Primary key constraint (`id uuid pk`)
- **unique**: Unique index (`email varchar unique`)
- **nullable**: Allow nulls (attributes are **NOT NULL by default**)
- **index**: Add secondary index (`name varchar index`)
- **`=default`**: Default value (`status varchar=active`, `created_at timestamp=`now()``)
- **`-> target_table(column)`**: Foreign key reference

## Relations (Inline)

```aml
orders
  id uuid pk
  user_id uuid -> users(id)
  shipping_address_id uuid -> addresses(id)
```

## Types (Custom / Enum)

```aml
type post_status (draft, published, archived)

posts
  id uuid pk
  status post_status=draft
```

## Namespaces (Database / Schema)

```aml
core.public.users
  id uuid pk
```

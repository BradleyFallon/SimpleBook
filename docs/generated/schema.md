# SimpleBook Output Schema

## Top-level

### Required fields
- `metadata`
- `chapters`

### Properties
- `metadata` (type: `object`)
- `chapters` (type: `array` | List of book chapters with their content)

## Metadata

### Required fields
- `title`
- `author`
- `language`

### Properties
- `title` (type: `string` | Book title)
- `author` (type: `string` | Book author/creator)
- `language` (type: `string` | Book language code (e.g., 'en', 'en-US'))
- `isbn` (type: `string` | ISBN identifier (if available))
- `uuid` (type: `string` | UUID identifier (if available))

## Chapters

## Chapter Item

### Required fields
- `name`
- `elements`
- `chunks`

### Properties
- `name` (type: `string` | Chapter name/title)
- `elements` (type: `array` | List of typed elements in the chapter)
- `chunks` (type: `array` | Element indexes at which new chunks start)

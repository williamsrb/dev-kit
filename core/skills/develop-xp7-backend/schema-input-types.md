# CMS Schema Input Types Quick Map

Use this file when implementing or reviewing schema fields in content types, mixins, or x-data.

Base docs:
- Input types root: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types>
- Field set: <https://developer.enonic.com/docs/xp/stable/cms/schemas/field-set>
- Item set: <https://developer.enonic.com/docs/xp/stable/cms/schemas/item-set>
- Option set: <https://developer.enonic.com/docs/xp/stable/cms/schemas/option-set>
- Localization: <https://developer.enonic.com/docs/xp/stable/cms/schemas/localization>

Input types:
- AttachmentUploader: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/attachmentuploader>
- Checkbox: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/checkbox>
- Combobox: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/combobox>
- ContentSelector: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/contentselector>
- ContentTypeFilter: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/contenttypefilter>
- CustomSelector: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/customselector>
- Date: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/date>
- DateTime: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/datetime>
- Double: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/double>
- GeoPoint: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/geopoint>
- HtmlArea: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/htmlarea>
- ImageSelector: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/imageselector>
- Long: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/long>
- MediaSelector: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/mediaselector>
- Radiobutton: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/radiobutton>
- Tag: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/tag>
- TextArea: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/textarea>
- TextLine: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/textline>
- Time: <https://developer.enonic.com/docs/xp/stable/cms/schemas/input-types/time>

## Practical backend notes

- Prefer stable field naming and avoid renames without migration planning.
- Treat selector-based fields as references that may require permission-aware resolution.
- Re-check index/query behavior when field cardinality or type changes.

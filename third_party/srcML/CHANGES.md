# CHANGES

This release of srcml is a drop-in replacement for the previous srcml client and libsrcml library. Except for Python, v1.1.0 does not make any changes to the markup for C, C++, Java, and C#. It does fix many markup bugs.

Major additions are:

* 1.0.0 markup for the Python programming language
* New query language srcQL, which allows querying by using code statements and includes unification, e.g., `FIND $T $N = new $T()`
* New output format for source with null separators (similar to `find`) and an optional YAML header with attributes and namespaces
* Additional libsrcml functions, including per-language versions, srcql, and complete control of attributes and namespaces for units and archives (see below)
* Multiple bug fixes, including more accurate line/column position
* Many build and packaging improvements

## libsrcml

The v1.1.0 libsrcml API supports all v1.0.0 libsrcml functions with no changes. The following are additional functions in the v1.1.0 libsrcml API. See the include file _srcml.h_ for more details.

```C
// per-language markup versions
int srcml_markup_version_number(const char* language);
const char* srcml_markup_version_string(const char* language);

// libsrcml version (separate from client version)
int srcml_libsrcml_version_number();
const char* srcml_libsrcml_version_string();

// srcql queries
int srcml_append_transform_srcql(struct srcml_archive* archive, const char* srcql_string);
int srcml_append_transform_srcql_attribute(struct srcml_archive* archive, const char* srcql_string,
int srcml_append_transform_srcql_element(struct srcml_archive* archive, const char* srcql_string,

// direct access to a unit's source
const char* srcml_unit_get_src(struct srcml_unit* unit);
ssize_t srcml_unit_get_src_size(struct srcml_unit* unit);

// attributes for units, archives, and convenience functions
int srcml_unit_add_attribute(struct srcml_unit* unit, const char* uri, const char* name, const char* value);
size_t srcml_unit_get_attribute_size(const struct srcml_unit* unit);
const char* srcml_unit_get_attribute_prefix(const struct srcml_unit* unit, size_t pos);
const char* srcml_unit_get_attribute_name(const struct srcml_unit* unit, size_t pos);
const char* srcml_unit_get_attribute_value(const struct srcml_unit* unit, size_t pos);
int srcml_archive_add_attribute(struct srcml_archive* archive, const char* uri, const char* name, const char* value);
size_t srcml_archive_get_attribute_size(const struct srcml_archive* archive);
const char* srcml_archive_get_attribute_prefix(const struct srcml_archive* archive, size_t pos);
const char* srcml_archive_get_attribute_name(const struct srcml_archive* archive, size_t pos);
const char* srcml_archive_get_attribute_value(const struct srcml_archive* archive, size_t pos);
int srcml_add_attribute(const char* uri, const char* name, const char* value);
size_t srcml_get_attribute_size();
const char* srcml_get_attribute_prefix(size_t pos);
const char* srcml_get_attribute_name(size_t pos);
const char* srcml_get_attribute_value(size_t pos);

// namespaces for a unit
int srcml_unit_register_namespace(struct srcml_unit* unit, const char* prefix, const char* uri);
size_t srcml_unit_get_namespace_size(const struct srcml_unit* unit);
const char* srcml_unit_get_namespace_prefix(const struct srcml_unit* unit, size_t pos);
const char* srcml_unit_get_prefix_from_uri(const struct srcml_unit* unit, const char* namespace_uri);
const char* srcml_unit_get_namespace_uri(const struct srcml_unit* unit, size_t pos);
const char* srcml_unit_get_uri_from_prefix(const struct srcml_unit* unit, const char* prefix);
```

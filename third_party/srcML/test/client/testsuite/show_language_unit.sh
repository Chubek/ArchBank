#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
#
# @file show_language_unit.sh
#
# @copyright Copyright (C) 2013-2024 srcML, LLC. (www.srcML.org)

# test framework
source $(dirname "$0")/framework_test.sh

define NEWLINE <<- 'STDOUT'
STDOUT

# test get language

# C++
defineXML srcmlcpp <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" directory="bar" filename="foo" version="1.2"/>
STDOUT

createfile sub/a.cpp.xml "$srcmlcpp"

srcml --show-language sub/a.cpp.xml
check "C++\n"

srcml --show-language < sub/a.cpp.xml
check "C++\n"

# Java
defineXML srcmljava <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="Java">
	</unit>
STDOUT

createfile sub/a.java.xml "$srcmljava"

srcml --show-language sub/a.java.xml
check "Java\n"

srcml --show-language < sub/a.java.xml
check "Java\n"

# C
defineXML srcmlc <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C">
	</unit>
STDOUT

createfile sub/a.c.xml "$srcmlc"

srcml --show-language sub/a.c.xml
check "C\n"

srcml --show-language < sub/a.c.xml
check "C\n"

# Objective-C
defineXML srcmlobjc <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="Objective-C">
	</unit>
STDOUT

createfile sub/a.m.xml "$srcmlobjc"

srcml --show-language sub/a.m.xml
check "Objective-C\n"

srcml --show-language < sub/a.m.xml
check "Objective-C\n"

# Aspect J
defineXML srcmlaj <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="Java">
	</unit>
STDOUT

createfile sub/a.aj.xml "$srcmlaj"

srcml --show-language sub/a.aj.xml
check "Java\n"

srcml --show-language < sub/a.aj.xml
check "Java\n"

# Empty
defineXML empty <<- 'STDIN'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="" directory="" filename="" version=""/>
STDIN

createfile sub/a.cpp.xml "$empty"

srcml --show-language sub/a.cpp.xml
check "\n"

srcml --show-language < sub/a.cpp.xml
check "\n"

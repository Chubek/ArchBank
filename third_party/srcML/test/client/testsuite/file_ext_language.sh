#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
#
# @file file_ext_language.sh
#
# @copyright Copyright (C) 2013-2024 srcML, LLC. (www.srcML.org)

# test framework
source $(dirname "$0")/framework_test.sh

# test
##
# check correct language based on file extension

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C" filename="emptysrc/empty.c"/>
STDOUT

createfile emptysrc/empty.c ""

srcml emptysrc/empty.c
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C" filename="emptysrc/empty.h"/>
STDOUT

createfile emptysrc/empty.h ""

srcml emptysrc/empty.h
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C" filename="emptysrc/empty.c"/>
STDOUT

createfile emptysrc/empty.c.gz ""

srcml emptysrc/empty.c.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C" filename="emptysrc/empty.h"/>
STDOUT

createfile emptysrc/empty.h.gz ""

srcml emptysrc/empty.h.gz
check "$checkvar"

#check c++ file extensions
defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.cpp"/>
STDOUT

createfile emptysrc/empty.cpp ""

srcml emptysrc/empty.cpp
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.cc"/>
STDOUT

createfile emptysrc/empty.cc ""

srcml emptysrc/empty.cc
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.cxx"/>
STDOUT

createfile emptysrc/empty.cxx ""

srcml emptysrc/empty.cxx
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.c++"/>
STDOUT

createfile emptysrc/empty.c++ ""

srcml emptysrc/empty.c++
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.hpp"/>
STDOUT

createfile emptysrc/empty.hpp ""

srcml emptysrc/empty.hpp
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.hh"/>
STDOUT

createfile emptysrc/empty.hh ""

srcml emptysrc/empty.hh
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.hxx"/>
STDOUT

createfile emptysrc/empty.hxx ""

srcml emptysrc/empty.hxx
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.h++"/>
STDOUT

createfile emptysrc/empty.h++ ""

srcml emptysrc/empty.h++
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.tcc"/>
STDOUT

createfile emptysrc/empty.tcc ""

srcml emptysrc/empty.tcc
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.cpp"/>
STDOUT

createfile emptysrc/empty.cpp.gz ""

srcml emptysrc/empty.cpp.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.cc"/>
STDOUT

createfile emptysrc/empty.cc.gz ""

srcml emptysrc/empty.cc.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.cxx"/>
STDOUT

createfile emptysrc/empty.cxx.gz ""

srcml emptysrc/empty.cxx.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.c++"/>
STDOUT

createfile emptysrc/empty.c++.gz ""

srcml emptysrc/empty.c++.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.hpp"/>
STDOUT

createfile emptysrc/empty.hpp.gz ""

srcml emptysrc/empty.hpp.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.hh"/>
STDOUT

createfile emptysrc/empty.hh.gz ""

srcml emptysrc/empty.hh.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.hxx"/>
STDOUT

createfile emptysrc/empty.hxx.gz ""

srcml emptysrc/empty.hxx.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.h++"/>
STDOUT

createfile emptysrc/empty.h++.gz ""

srcml emptysrc/empty.h++.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="C++" filename="emptysrc/empty.tcc"/>
STDOUT

createfile emptysrc/empty.tcc.gz ""

srcml emptysrc/empty.tcc.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="Java" filename="emptysrc/empty.java"/>
STDOUT

# check java file extension
createfile emptysrc/empty.java ""

srcml emptysrc/empty.java
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="Java" filename="emptysrc/empty.java"/>
STDOUT

createfile emptysrc/empty.java.gz ""

srcml emptysrc/empty.java.gz
check "$checkvar"

defineXML checkvar <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION" language="Java" filename="emptysrc/empty.aj"/>
STDOUT

createfile emptysrc/empty.aj.gz ""

srcml emptysrc/empty.aj.gz
check "$checkvar"

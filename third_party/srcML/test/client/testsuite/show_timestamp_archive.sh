#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
#
# @file show_timestamp_archive.sh
#
# @copyright Copyright (C) 2013-2024 srcML, LLC. (www.srcML.org)

# test framework
source $(dirname "$0")/framework_test.sh

# test get directory
defineXML archive <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION">

	<unit revision="REVISION" language="C++" filename="a.cpp" hash="1a2c5d67e6f651ae10b7673c53e8c502c97316d6">
	<expr_stmt><expr><name>a</name></expr>;</expr_stmt>
	</unit>

	</unit>
STDOUT

createfile sub/archive.cpp.xml "$archive"

srcml --show-timestamp sub/archive.cpp.xml
check

srcml --show-timestamp < sub/archive.cpp.xml
check

# empty
defineXML empty <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION">

	<unit revision="REVISION" language="C++" filename="a.cpp" hash="1a2c5d67e6f651ae10b7673c53e8c502c97316d6">
	<expr_stmt><expr><name>a</name></expr>;</expr_stmt>
	</unit>

	</unit>
STDOUT

createfile sub/archive.cpp.xml "$empty"

srcml --show-timestamp sub/archive.cpp.xml
check

srcml --show-timestamp < sub/archive.cpp.xml
check

# none
defineXML none <<- 'STDIN'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" revision="REVISION">

	<unit revision="REVISION" language="C++" filename="a.cpp" hash="1a2c5d67e6f651ae10b7673c53e8c502c97316d6">
	<expr_stmt><expr><name>a</name></expr>;</expr_stmt>
	</unit>

	</unit>
STDIN

createfile sub/archive.cpp.xml "$none"

srcml --show-timestamp sub/archive.cpp.xml
check

srcml --show-timestamp < sub/archive.cpp.xml
check

#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-only
#
# @file srcql_select_attribute_archive_multi.sh
#
# @copyright Copyright (C) 2013-2024 srcML, LLC. (www.srcML.org)

# test framework
source $(dirname "$0")/framework_test.sh

# test xpath query for attribute info
defineXML srcml <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:st="http://www.srcML.org/srcML/stereotype" revision="REVISION" >

	<unit revision="REVISION" language="C++" filename="b.cpp" hash="17239ee1ffe4b0abc790a338f52d2ac2f2565c4e">
	<class st:stereotype="commander">class <name>Logger</name> <block>{<private type="default">
	</private><public>public:
	    <function><type><specifier>static</specifier> <name>Logger</name><modifier>*</modifier></type> <name>instance</name><parameter_list>()</parameter_list> <block>{<block_content>
	        <if_stmt><if>if<condition>(<expr><name>internal_inst</name> <operator>==</operator> <literal type="null">nullptr</literal></expr>)</condition> <block>{<block_content> <expr_stmt><expr><name>internal_inst</name> <operator>=</operator> <operator>new</operator> <name>Logger</name></expr>;</expr_stmt> </block_content>}</block></if></if_stmt>
	        <return>return <expr><name>internal_inst</name></expr>;</return>
	    </block_content>}</block></function>
	    <function st:stereotype="command collaborator"><template>template<parameter_list>&lt;<parameter><type><name>typename</name></type> <name>T</name></parameter>&gt;</parameter_list></template>
	    <type><name>void</name></type> <name>writeLine</name><parameter_list>(<parameter><decl><type><specifier>const</specifier> <name>char</name><modifier>*</modifier></type> <name>type</name></decl></parameter>, <parameter><decl><type><specifier>const</specifier> <name>T</name><modifier>&amp;</modifier></type> <name>text</name></decl></parameter>)</parameter_list> <block>{<block_content>
	        <if_stmt><if>if<condition>(<expr><name>lineEnded</name></expr>)</condition> <block>{<block_content> <expr_stmt><expr><call><name>writeTime</name><argument_list>()</argument_list></call></expr>;</expr_stmt> </block_content>}</block></if></if_stmt>
	        <expr_stmt><expr><name>log</name> <operator>&lt;&lt;</operator> <literal type="string">"["</literal> <operator>&lt;&lt;</operator> <name>type</name> <operator>&lt;&lt;</operator> <literal type="string">"] "</literal> <operator>&lt;&lt;</operator> <name>text</name> <operator>&lt;&lt;</operator> <name><name>std</name><operator>::</operator><name>endl</name></name></expr>;</expr_stmt>
	        <expr_stmt><expr><name>lineEnded</name> <operator>=</operator> <literal type="boolean">true</literal></expr>;</expr_stmt>
	    </block_content>}</block></function>
	    <function st:stereotype="set"><type><name>void</name></type> <name>close</name><parameter_list>()</parameter_list> <block>{<block_content>
	        <expr_stmt><expr><call><name><name>log</name><operator>.</operator><name>close</name></name><argument_list>()</argument_list></call></expr>;</expr_stmt>
	    </block_content>}</block></function>
	</public><private>private:
	    <constructor st:stereotype="constructor"><name>Logger</name><parameter_list>()</parameter_list> <block>{<block_content> <expr_stmt><expr><name>log</name> <operator>=</operator> <call><name><name>std</name><operator>::</operator><name>ofstream</name></name><argument_list>(<argument><expr><literal type="string">"output_log.txt"</literal></expr></argument>)</argument_list></call></expr>;</expr_stmt> <expr_stmt><expr><call><name>writeTime</name><argument_list>()</argument_list></call></expr>;</expr_stmt> <expr_stmt><expr><call><name>writeLine</name><argument_list>(<argument><expr><literal type="string">"INFO"</literal></expr></argument>,<argument><expr><literal type="string">"Log file created"</literal></expr></argument>)</argument_list></call></expr>;</expr_stmt> </block_content>}</block></constructor><empty_stmt>;</empty_stmt>
	    <function st:stereotype="wrapper"><type><name>void</name></type> <name>writeTime</name><parameter_list>()</parameter_list> <block>{<block_content>
	        <expr_stmt><expr><name>log</name> <operator>&lt;&lt;</operator> <call><name><name>QDateTime</name><operator>::</operator><name>currentDateTime</name></name><argument_list>()</argument_list></call><operator>.</operator><call><name>toString</name><argument_list>()</argument_list></call><operator>.</operator><call><name>toUtf8</name><argument_list>()</argument_list></call><operator>.</operator><call><name>constData</name><argument_list>()</argument_list></call> <operator>&lt;&lt;</operator> <literal type="char">' '</literal></expr>;</expr_stmt>
	    </block_content>}</block></function>
	    <constructor st:stereotype="copy-constructor"><name>Logger</name><parameter_list>(<parameter><decl><type><specifier>const</specifier> <name>Logger</name><modifier>&amp;</modifier></type></decl></parameter>)</parameter_list> <block>{<block_content/>}</block></constructor>
	    <function type="operator" st:stereotype="empty"><type><name>Logger</name><modifier>&amp;</modifier></type> <name>operator<name>=</name></name><parameter_list>(<parameter><decl><type><specifier>const</specifier> <name>Logger</name><modifier>&amp;</modifier></type></decl></parameter>)</parameter_list> <block>{<block_content/>}</block></function>
	    <decl_stmt><decl><type><specifier>static</specifier> <name>Logger</name><modifier>*</modifier></type> <name>internal_inst</name></decl>;</decl_stmt>
	    <decl_stmt><decl><type><name><name>std</name><operator>::</operator><name>ofstream</name></name></type> <name>log</name></decl>;</decl_stmt>
	    <decl_stmt><decl><type><name>bool</name></type> <name>lineEnded</name> <init>= <expr><literal type="boolean">false</literal></expr></init></decl>;</decl_stmt>
	</private>}</block>;</class>
	</unit>

	</unit>
STDOUT

createfile sub/srcql_attr_select.xml "$srcml"

# select any stereotype
defineXML withAttr <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:st="http://www.srcML.org/srcML/stereotype" revision="1.0.0">
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="1"><function st:stereotype="command collaborator"><template>template<parameter_list>&lt;<parameter><type><name>typename</name></type> <name>T</name></parameter>&gt;</parameter_list></template>
	    <type><name>void</name></type> <name>writeLine</name><parameter_list>(<parameter><decl><type><specifier>const</specifier> <name>char</name><modifier>*</modifier></type> <name>type</name></decl></parameter>, <parameter><decl><type><specifier>const</specifier> <name>T</name><modifier>&amp;</modifier></type> <name>text</name></decl></parameter>)</parameter_list> <block>{<block_content>
	        <if_stmt><if>if<condition>(<expr><name>lineEnded</name></expr>)</condition> <block>{<block_content> <expr_stmt><expr><call><name>writeTime</name><argument_list>()</argument_list></call></expr>;</expr_stmt> </block_content>}</block></if></if_stmt>
	        <expr_stmt><expr><name>log</name> <operator>&lt;&lt;</operator> <literal type="string">"["</literal> <operator>&lt;&lt;</operator> <name>type</name> <operator>&lt;&lt;</operator> <literal type="string">"] "</literal> <operator>&lt;&lt;</operator> <name>text</name> <operator>&lt;&lt;</operator> <name><name>std</name><operator>::</operator><name>endl</name></name></expr>;</expr_stmt>
	        <expr_stmt><expr><name>lineEnded</name> <operator>=</operator> <literal type="boolean">true</literal></expr>;</expr_stmt>
	    </block_content>}</block></function></unit>
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="2"><function st:stereotype="set"><type><name>void</name></type> <name>close</name><parameter_list>()</parameter_list> <block>{<block_content>
	        <expr_stmt><expr><call><name><name>log</name><operator>.</operator><name>close</name></name><argument_list>()</argument_list></call></expr>;</expr_stmt>
	    </block_content>}</block></function></unit>
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="3"><function st:stereotype="wrapper"><type><name>void</name></type> <name>writeTime</name><parameter_list>()</parameter_list> <block>{<block_content>
	        <expr_stmt><expr><name>log</name> <operator>&lt;&lt;</operator> <call><name><name>QDateTime</name><operator>::</operator><name>currentDateTime</name></name><argument_list>()</argument_list></call><operator>.</operator><call><name>toString</name><argument_list>()</argument_list></call><operator>.</operator><call><name>toUtf8</name><argument_list>()</argument_list></call><operator>.</operator><call><name>constData</name><argument_list>()</argument_list></call> <operator>&lt;&lt;</operator> <literal type="char">' '</literal></expr>;</expr_stmt>
	    </block_content>}</block></function></unit>
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="4"><function type="operator" st:stereotype="empty"><type><name>Logger</name><modifier>&amp;</modifier></type> <name>operator<name>=</name></name><parameter_list>(<parameter><decl><type><specifier>const</specifier> <name>Logger</name><modifier>&amp;</modifier></type></decl></parameter>)</parameter_list> <block>{<block_content/>}</block></function></unit>
	
	</unit>
STDOUT

srcml sub/srcql_attr_select.xml --srcql='FIND src:function WITH st:stereotype' --srcql-warning-off
check "$withAttr"

# select specific stereotype
defineXML withSpecificAttr <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:st="http://www.srcML.org/srcML/stereotype" revision="1.0.0">
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="1"><function st:stereotype="set"><type><name>void</name></type> <name>close</name><parameter_list>()</parameter_list> <block>{<block_content>
	        <expr_stmt><expr><call><name><name>log</name><operator>.</operator><name>close</name></name><argument_list>()</argument_list></call></expr>;</expr_stmt>
	    </block_content>}</block></function></unit>
	
	</unit>
STDOUT

srcml sub/srcql_attr_select.xml --srcql='FIND src:function WITH st:stereotype = set' --srcql-warning-off
check "$withSpecificAttr"

# select a specific stereotype
defineXML withASpecificAttr <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:st="http://www.srcML.org/srcML/stereotype" revision="1.0.0">
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="1"><function st:stereotype="command collaborator"><template>template<parameter_list>&lt;<parameter><type><name>typename</name></type> <name>T</name></parameter>&gt;</parameter_list></template>
	    <type><name>void</name></type> <name>writeLine</name><parameter_list>(<parameter><decl><type><specifier>const</specifier> <name>char</name><modifier>*</modifier></type> <name>type</name></decl></parameter>, <parameter><decl><type><specifier>const</specifier> <name>T</name><modifier>&amp;</modifier></type> <name>text</name></decl></parameter>)</parameter_list> <block>{<block_content>
	        <if_stmt><if>if<condition>(<expr><name>lineEnded</name></expr>)</condition> <block>{<block_content> <expr_stmt><expr><call><name>writeTime</name><argument_list>()</argument_list></call></expr>;</expr_stmt> </block_content>}</block></if></if_stmt>
	        <expr_stmt><expr><name>log</name> <operator>&lt;&lt;</operator> <literal type="string">"["</literal> <operator>&lt;&lt;</operator> <name>type</name> <operator>&lt;&lt;</operator> <literal type="string">"] "</literal> <operator>&lt;&lt;</operator> <name>text</name> <operator>&lt;&lt;</operator> <name><name>std</name><operator>::</operator><name>endl</name></name></expr>;</expr_stmt>
	        <expr_stmt><expr><name>lineEnded</name> <operator>=</operator> <literal type="boolean">true</literal></expr>;</expr_stmt>
	    </block_content>}</block></function></unit>
	
	</unit>
STDOUT

srcml sub/srcql_attr_select.xml --srcql='FIND src:function WITH st:stereotype ~= command' --srcql-warning-off
check "$withASpecificAttr"

# select expressions with strings
defineXML exprOutput <<- 'STDOUT'
	<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
	<unit xmlns="http://www.srcML.org/srcML/src" xmlns:st="http://www.srcML.org/srcML/stereotype" revision="1.0.0">
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="1"><expr><name>log</name> <operator>&lt;&lt;</operator> <literal type="string">"["</literal> <operator>&lt;&lt;</operator> <name>type</name> <operator>&lt;&lt;</operator> <literal type="string">"] "</literal> <operator>&lt;&lt;</operator> <name>text</name> <operator>&lt;&lt;</operator> <name><name>std</name><operator>::</operator><name>endl</name></name></expr></unit>
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="2"><expr><name>log</name> <operator>=</operator> <call><name><name>std</name><operator>::</operator><name>ofstream</name></name><argument_list>(<argument><expr><literal type="string">"output_log.txt"</literal></expr></argument>)</argument_list></call></expr></unit>
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="3"><expr><literal type="string">"output_log.txt"</literal></expr></unit>
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="4"><expr><call><name>writeLine</name><argument_list>(<argument><expr><literal type="string">"INFO"</literal></expr></argument>,<argument><expr><literal type="string">"Log file created"</literal></expr></argument>)</argument_list></call></expr></unit>
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="5"><expr><literal type="string">"INFO"</literal></expr></unit>
	
	<unit revision="1.0.0" language="C++" filename="b.cpp" item="6"><expr><literal type="string">"Log file created"</literal></expr></unit>
	
	</unit>
STDOUT

srcml sub/srcql_attr_select.xml --srcql='FIND $E CONTAINS src:literal WITH type = string'
check "$exprOutput"

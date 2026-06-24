// SPDX-License-Identifier: GPL-3.0-only
/**
 * @file DocstringPython.hpp
 *
 * @copyright Copyright (C) 2024 srcML, LLC. (www.srcML.org)
 *
 * This file is part of the srcML Toolkit.
 *
 * Changes certain statement keywords to names in Python.
 * Impacts `case`, `exec`, `match`, `print`, and `type`.
 */

#include <NameDifferentiatorPython.hpp>

// Converts certain statement keyword tokens to names
antlr::RefToken NameDifferentiatorPython::nextToken() {
    // place all input tokens in a buffer to help check for keywords that should be names
    if (buffer.empty()) {
        auto token = input.nextToken();

        switch (token->getType()) {
            // Change `exec`, `print`, or `type` to names (if applicable)
            case srcMLParser::PY_2_EXEC:
            case srcMLParser::PY_2_PRINT:
            case srcMLParser::PY_TYPE:
                lookAheadTwoDifferentiator(token);
                break;

            // Change `case` or `match` to names (if applicable)
            case srcMLParser::PY_CASE:
            case srcMLParser::PY_MATCH:
                variableLookAheadDifferentiator(token);
                break;
    
            default:
                checkBracketToken(token);  // Detect if currently in/out of `()`, `{}`, or `[]`
                break;
        }

        // insert read token
        buffer.emplace_front(token);
    }

    // next token
    auto token = buffer.front();
    buffer.pop_front();
    return token;
}

/**
 * Uses the next two tokens after `token` to check if a keyword should be a name.
 * 
 * Supports Python soft keywords `exec`, `print`, and `type`.
 */
void NameDifferentiatorPython::lookAheadTwoDifferentiator(antlr::RefToken token) {
    bool isTopLevel = (numBrackets == 0);  // statements cannot exist inside brackets

    auto nextToken = input.nextToken();
    checkBracketToken(nextToken);  // Detect if currently in/out of `()`, `{}`, or `[]`
    buffer.emplace_back(nextToken);

    auto extraToken = input.nextToken();
    checkBracketToken(extraToken);  // Detect if currently in/out of `()`, `{}`, or `[]`
    buffer.emplace_back(extraToken);

    switch (token->getType()) {
        // Check if `exec` or `print` should be names or keywords
        case srcMLParser::PY_2_EXEC:
        case srcMLParser::PY_2_PRINT: {
            // `print` and `exec` are statements if followed by WS + non-LPAREN token at the top level
            if (
                isTopLevel
                && (nextToken->getType() != srcMLParser::WS || extraToken->getType() == srcMLParser::LPAREN)
            )
                token->setType(srcMLParser::NAME);

            break;
        }

        // Check if `type` should be a name or keyword
        case srcMLParser::PY_TYPE: {
            // `type` is a statement if followed by WS (or WS + NAME) at the top level
            if (
                isTopLevel
                && (
                    nextToken->getType() != srcMLParser::WS
                    || (
                        extraToken->getType() != srcMLParser::NAME
                        && !srcMLParser::identifier_list_tokens_set.member(extraToken->getType())
                    )
                )
            )
                token->setType(srcMLParser::NAME);

            break;
        }

        default:
            break;
    }
}

/**
 * Uses (at least) the next token after `token` to check if a keyword should be a name.
 * 
 * A nested soft keyword should always be marked as a `NAME`;
 * That logic goes in `identifier_list[]` in `srcMLParser.g` and
 * its corresponding bitset token set, not here.
 * 
 * Supports Python soft keywords `case` and `match`.
 */
void NameDifferentiatorPython::variableLookAheadDifferentiator(antlr::RefToken token) {
    bool skipProcessing = false;
    numCurrentBrackets = numBrackets;  // ensure block start token is not buried in brackets
    isName = true;  // assume `token` is a name until shown otherwise

    auto nextToken = input.nextToken();
    checkBracketToken(nextToken);  // Detect if currently in/out of `()`, `{}`, or `[]`
    buffer.emplace_back(nextToken);

    // `token` + `:` should automatically set `token` to a NAME (for type annotations)
    // if `try` ever becomes a soft keyword, this entire method will break
    if (nextToken->getType() == blockStartToken)
        skipProcessing = true;

    if (!skipProcessing) {
        // look for a block start token or a newline (if numCurrentBrackets == numBrackets)
        while (true) {
            nextToken = input.nextToken();
            checkBracketToken(nextToken);  // Detect if currently in/out of `()`, `{}`, or `[]`
            buffer.emplace_back(nextToken);

            // [NOT A NAME] failsafe to break out of the loop
            if (nextToken->getType() == srcMLParser::EOF_) {
                isName = false;
                break;
            }

            // [IS A NAME] found a newline not buried inside additional brackets
            if (
                (nextToken->getType() == srcMLParser::EOL || nextToken->getType() == srcMLParser::WS_EOL)
                && numBrackets == numCurrentBrackets
            )
                break;

            // [NOT A NAME] found a block start token
            if (nextToken->getType() == blockStartToken && numBrackets == numCurrentBrackets) {
                isName = false;
                break;
            }
        }
    }

    if (isName)
        token->setType(srcMLParser::NAME);
}

/**
 * Detects opening and closing brackets (e.g., `()`, `{}`, and `[]`).
 * 
 * Ensures certain colon (`:`) tokens do not start blocks in Python.
 * Examples including array slicing, dictionairies, and type annotations.
 * 
 * Operates under the assumption the code contains balanced brackets.
 */
void NameDifferentiatorPython::checkBracketToken(antlr::RefToken token) {
    if (srcMLParser::left_bracket_py_token_set.member(token->getType()))
        ++numBrackets;
    else if (numBrackets > 0 && srcMLParser::right_bracket_py_token_set.member(token->getType()))
        --numBrackets;
}

/**
 * Assigns the value of `token` to `blockStartToken`.
 * 
 * Existing logic was built around the colon (`:`) in Python.
 * Other values may not work as expected, especially in niche situations.
 * 
 * Refer to `srcMLParserTokenTypes.hpp` for all supported values.
 */
void NameDifferentiatorPython::setBlockStartToken(int token) {
    blockStartToken = token;
}

/**
 * Returns `blockStartToken`.
 */
int NameDifferentiatorPython::getBlockStartToken() const {
    return blockStartToken;
}

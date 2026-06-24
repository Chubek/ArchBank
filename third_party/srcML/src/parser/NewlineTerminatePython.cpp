// SPDX-License-Identifier: GPL-3.0-only
/**
 * @file NewlineTerminatePython.hpp
 *
 * @copyright Copyright (C) 2024 srcML, LLC. (www.srcML.org)
 *
 * This file is part of the srcML Toolkit.
 *
 * Injects INDENT and DEDENT tokens to the token stream
 */

#include <NewlineTerminatePython.hpp>

// Inserts TERMINATE tokens at EOL for Python
antlr::RefToken NewlineTerminatePython::nextToken() {

    // place all input tokens in the buffer so we can insert a TERMINATE
    if (buffer.empty()) {
        auto token = input.nextToken();

        // buffer any non-EOL whitespace or line continuation backslashes
        // since these must be placed after the inserted terminate
        std::deque<antlr::RefToken> wsBuffer;
        while (token->getType() == srcMLParser::WS || token->getType() == srcMLParser::EOL_BACKSLASH) {
            wsBuffer.emplace_back(token);
            token = input.nextToken();
        }

        // update the open parentheses count
        if (srcMLParser::left_bracket_py_token_set.member(token->getType()))
            ++parenthesesCount;
        else if (parenthesesCount > 0 && srcMLParser::right_bracket_py_token_set.member(token->getType()))
            --parenthesesCount;

        // For a newline, insert a TERMINATE in certain cases
        if (((token->getType() == srcMLParser::EOL ||
              token->getType() == srcMLParser::WS_EOL ||
              token->getType() == srcMLParser::HASHTAG_COMMENT_START ||
              token->getType() == srcMLParser::HASHBANG_COMMENT_START) &&

            // not in parentheses
            parenthesesCount == 0 &&

            // not an empty line
            !firstCharacter &&

            // not an existing TERMINATE
            lastToken->getType() != srcMLParser::TERMINATE &&

            // // not a whitespace line
            // !isWhitespaceLine &&

            // no inserted INDENT, which implies a block
            lastToken->getType() != srcMLParser::INDENT &&

            // not in the middle of an expression with a previous operator
            // Python does not have any postfix operators, so an operator at the end means the expression is not complete
            lastNonWhitespaceToken->getType() != srcMLParser::OPERATORS &&
            lastNonWhitespaceToken->getType() != srcMLParser::TEMPOPE &&
            lastNonWhitespaceToken->getType() != srcMLParser::TEMPOPS) ||

            // At EOF with no previous EOL
            (token->getType() == 1 /* EOF */ && lastToken->getType() != srcMLParser::EOL)) {

            // create new terminate token
            auto terminateToken = srcMLToken::factory();
            terminateToken->setType(srcMLParser::TERMINATE);
            terminateToken->setColumn(1);
            terminateToken->setLine(token->getLine());

            // reset the parentheses count
            parenthesesCount = 0;

            // insert terminal token
            buffer.emplace_back(terminateToken);
        }

        if (token->getType() == srcMLParser::EOL) {
            firstCharacter = true;
            isEmptyLine = true;
        } else if (token->getType() != srcMLParser::WS) {
            firstCharacter = false;
            isEmptyLine = false;
        }

        // record to check for previous INDENT
        lastToken = token;

        // insert skipped whitespace
        while (!wsBuffer.empty()) {
            buffer.emplace_back(wsBuffer.front());
            wsBuffer.pop_front();
        }

        // insert read token
        buffer.emplace_back(token);
    }

    // next token
    auto token = buffer.front();
    buffer.pop_front();
    return token;
}

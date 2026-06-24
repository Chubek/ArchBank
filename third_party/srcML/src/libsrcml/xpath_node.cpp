#include "xpath_node.hpp"

XPathNode::XPathNode(const XPathNode& orig, bool special_copy) {
    text = orig.text;
    type = orig.type;
    for (auto child : orig.children) {
        // Special copy is for the following-sibling count predicates, where we don't want a true deep copy
        if (!special_copy || (child->type == PREDICATE && (child->text.find("text()=") == 0 || child->text == "qli:is-valid-element(.)"))) {
            add_child(new XPathNode(*child));
        }
    }
}


XPathNode::~XPathNode() {
    if (!children.empty()) {
        for (auto child : children) {
            delete child;
        }
    }
}

std::ostream& operator<<(std::ostream& out, const XPathNode& node) {
    if (node.type == PREDICATE)        { out << '['  ; }
    else if (node.type == PARENTHESES) { out << '('  ; }
    else if (node.type == NEXT)        { out << '/'  ; }
    else if (node.type == ANY)         { out << "//" ; }
    else if (node.type == UNION)       { out << "|"  ; }

    if (node.type != UNION) { out << node.text; };
    if (node.type == PARENTHESES) { out << ')'; }
    if (node.type != CALL) {
        for (auto child : node.children) { out << *child; }
    }
    else {
        out << "(";
        size_t i = 0;
        bool union_child = false;
        for (auto child : node.children) {
            if (child->get_type() == UNION) {
                union_child = true;
                break;
            }
            if (i != 0) { out << ","; }
            out << *child;
            ++i;
        }
        out << ")";
        if (union_child) {
            out << *node.children[i];
        }
    }

    if (node.type == PREDICATE)        { out << ']' ; }

    return out;
}

std::string XPathNode::to_string(std::string_view rtn_view) {
    std::string rtn(rtn_view);
    if (type == PREDICATE)        { rtn += '['  ; }
    else if (type == PARENTHESES) { rtn += '('  ; }
    else if (type == NEXT)        { rtn += '/'  ; }
    else if (type == ANY)         { rtn += "//" ; }
    else if (type == UNION)       { rtn += "|"  ; }

    if (type != UNION) { rtn += text; };
    if (type == PARENTHESES) { rtn += ')'; }
    if (type != CALL) {
        for (auto child : children) { rtn += child->to_string(); }
    }
    else {
        rtn += "(";
        size_t i = 0;
        bool union_child = false;
        for (auto child : children) {
            if (child->get_type() == UNION) {
                union_child = true;
                break;
            }
            if (i != 0) { rtn += ","; }
            rtn += child->to_string();
            ++i;
        }
        rtn += ")";
        if (union_child) {
            rtn += children[i]->to_string();
        }
    }

    if (type == PREDICATE)        { rtn += ']' ; }

    return rtn;
}

void XPathNode::pretty_print(int tabs) {
    if (type == PREDICATE)        { std::cout << '\n'; tabs++; for(int i = 0; i < tabs; ++i) { std::cout << "\t"; } std::cout << '['  ; }
    else if (type == PARENTHESES) { std::cout << '('  ; }
    else if (type == NEXT)        { std::cout << '/'  ; }
    else if (type == ANY)         { std::cout << "//" ; }
    else if (type == UNION)       { std::cout << "|"  ; }

    if (type != UNION) { std::cout << text; };
    if (type == PARENTHESES) { std::cout << ')'; }
    if (type != CALL) {
        for (auto child : children) { child->pretty_print(tabs); }
    }
    else {
        std::cout << "(";
        size_t i = 0;
        bool union_child = false;
        for (auto child : children) {
            if (child->get_type() == UNION) {
                union_child = true;
                break;
            }
            if (i != 0) { std::cout << ","; }
            child->pretty_print(tabs);
            ++i;
        }
        std::cout << ")";
        if (union_child) {
            children[i]->pretty_print(tabs);
        }
    }

    if (type == PREDICATE)        { std::cout << "]" ; }
}

XPathNode* XPathNode::pop_child_beginning() {
    if (children.size()) {
        XPathNode* rtn = children.front();
        children.pop_front();
        return rtn;
    }
    return nullptr;
}

XPathNode* XPathNode::pop_child_end() {
    if (children.size()) {
        XPathNode* rtn = children.back();
        children.pop_back();
        return rtn;
    }
    return nullptr;
}

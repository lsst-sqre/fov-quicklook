import ast


class DefinitionReplacer(ast.NodeTransformer):
    def __init__(self, target_path, new_code):
        self.target_path = target_path.split('.')
        self.new_code = new_code
        self.current_path = []

    def visit_ClassDef(self, node):
        self.current_path.append(node.name)
        self.generic_visit(node)
        self.current_path.pop()
        return node

    def visit_FunctionDef(self, node):
        self.current_path.append(node.name)
        if self.is_target_node():
            return ast.parse(self.new_code).body[0]
        self.current_path.pop()
        return node

    def visit_AnnAssign(self, node):
        if hasattr(node.target, 'id'):  # Variable assignment
            self.current_path.append(node.target.id)  # type: ignore
            if self.is_target_node():
                return ast.parse(self.new_code).body[0]
            self.current_path.pop()
        return node

    def is_target_node(self):
        return self.current_path == self.target_path


def replace_definition(codes, target_path, new_code):
    tree = ast.parse(codes)
    replacer = DefinitionReplacer(target_path, new_code)
    new_tree = replacer.visit(tree)
    return ast.unparse(new_tree)


class TypeAnnotationReplacer(ast.NodeTransformer):
    def __init__(self, original_type, new_type):
        super().__init__()
        self.original_type = original_type
        self.new_type = new_type

    def visit_AnnAssign(self, node):
        if self.is_target_annotation(node.annotation):
            node.annotation.value.id = self.new_type  # type: ignore
        return node

    def visit_arg(self, node):
        if self.is_target_annotation(node.annotation):
            node.annotation.value.id = self.new_type  # type: ignore
        return node

    def is_target_annotation(self, annotation):
        return isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name) and annotation.value.id == self.original_type


def replace_type_annotation(codes, original_type, new_type):
    tree = ast.parse(codes)
    replacer = TypeAnnotationReplacer(original_type, new_type)
    new_tree = replacer.visit(tree)
    return ast.unparse(new_tree)


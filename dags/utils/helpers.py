from pathlib import Path

"""
Helper functions to support the DAGs, such as path handling and other utilities.
"""
def get_path_to_file(folder: str, file_name: str) -> Path:
    """
    Helper function to resolve path to a file in the DAGs folder structure.
    """
    # Get base dags folder path
    dags_base_path = Path(__file__).parent.parent
    path = dags_base_path / folder / file_name
    if not path.exists():
        raise FileNotFoundError(f"File not found for path: {path}")
    
    return path

def render_sql_template(sql: str, template_variables: dict) -> str:
    """
    Helper function to render a SQL template using Jinja based on the provided variables.
    """
    from jinja2 import Template
    template = Template(sql)
    rendered_sql = template.render(**template_variables)

    return rendered_sql

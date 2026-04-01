from pathlib import Path

from robot_sim.app.version_catalog import current_version_catalog


def test_docs_version_alignment(project_root):
    catalog = current_version_catalog()
    readme = (Path(project_root) / 'README.md').read_text(encoding='utf-8')
    roadmap = (Path(project_root) / 'docs' / 'roadmap.md').read_text(encoding='utf-8')
    schema = (Path(project_root) / 'docs' / 'schema_versions.md').read_text(encoding='utf-8')
    assert catalog.roadmap_version in roadmap
    assert catalog.docs_release_label.split()[0] in readme
    assert catalog.export_schema_version in schema

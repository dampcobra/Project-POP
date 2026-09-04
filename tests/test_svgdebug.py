from layercake_spike import spec, svgdebug, topology


def build():
    return topology.Partition.build(spec.REGIONS)


def test_svg_contains_every_region_and_marks_shared_edges(tmp_path):
    out = tmp_path / "debug.svg"
    svg = svgdebug.render(build(), out)
    assert out.exists()
    assert svg.startswith("<?xml")
    for rid in ("A", "B", "C"):
        assert f'data-region="{rid}"' in svg
    assert 'class="shared-edge"' in svg


def test_svg_marks_reflex_vertices_so_concavity_is_inspectable(tmp_path):
    svg = svgdebug.render(build(), tmp_path / "debug.svg")
    assert 'class="reflex"' in svg


def test_svg_is_well_formed_xml(tmp_path):
    import xml.etree.ElementTree as ET

    svgdebug.render(build(), tmp_path / "debug.svg")
    ET.parse(tmp_path / "debug.svg")  # must not raise


def test_hole_is_rendered_so_the_island_is_visibly_a_hole(tmp_path):
    svg = svgdebug.render(build(), tmp_path / "debug.svg")
    # B's path must carry two subpaths: its outer ring and the C cavity
    b_path = [ln for ln in svg.splitlines() if 'data-region="B"' in ln][0]
    assert b_path.count("M ") == 2
    assert 'fill-rule="evenodd"' in b_path

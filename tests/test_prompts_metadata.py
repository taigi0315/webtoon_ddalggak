import pytest

from app.prompts import loader


def test_metadata_extraction_and_validation():
    meta = loader.get_prompt_metadata("test_prompt_with_meta")
    assert meta["domain"] == "utility"
    assert "name" in meta["variables"]
    assert set(meta["required_variables"]) == {"name", "age"}
    assert isinstance(meta["output_schema"], dict)

    # Validate output validator works
    valid_output = {"greeting": "Hello A", "age": 30}
    assert loader.validate_prompt_output("test_prompt_with_meta", valid_output)

    invalid_output = {"age": 30}
    with pytest.raises(ValueError):
        loader.validate_prompt_output("test_prompt_with_meta", invalid_output)

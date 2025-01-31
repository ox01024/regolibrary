import json
import os
import re

FRAMEWORK_DIR = "frameworks"
CONTROLS_DIR = "controls"
RULES_DIR = "rules"
ATTACK_TRACKS_DIR = "attack-tracks"
RULES_CHECKED = set()
CONTROLID_TO_FILENAME = {}
RULENAME_TO_RULE_DIR = {}
ATTACK_TRACKS_DICT = {}

def ignore_file(file_name: str):
    return file_name.startswith('__')

# Test that each control ID in a framework file has a corresponding control file in the "controls" directory
def validate_controls_in_framework():
    framework_files = os.listdir(FRAMEWORK_DIR)
    for framework_file in framework_files:
        if ignore_file(framework_file):
            continue
        with open(os.path.join(FRAMEWORK_DIR, framework_file), "r") as f:
            framework = json.load(f)

            for control in framework["activeControls"]:
                control_id = control["controlID"]
                # validate control exists and name is according to convention
                assert control_id in CONTROLID_TO_FILENAME, f"No file found for Control ID {control_id}."

# validate if each control has scanning scope and allowed one
def validate_control_scanning_scope(control):
    allowed_scopes = [["cluster", "file"], ["cluster"], ["cloud"], ["GKE"], ["EKS"], ["AKS"]]
    controlID=control["controlID"]

    scanning_scopes = control["scanningScope"]
    assert scanning_scopes != None, f"control {controlID} has no [\"scanningScope\"] field"

    scanning_scopes_match = scanning_scopes["matches"]
    assert scanning_scopes != None, f"control {controlID} has no [\"scanningScope\"][\"matches\"] fields"

    scope_allowed_check = False
    for allowed_scope in allowed_scopes:
        if scanning_scopes_match == allowed_scope:
            scope_allowed_check = True
            break
    assert scope_allowed_check == True, f"control {controlID} has no allowed scope"

def extract_sub_steps(step):
    """Recursive function to extract all sub-step names."""
    sub_step_names = set()
    
    # Add the current step's name (if present)
    if "name" in step:
        sub_step_names.add(step["name"])
    
    # Recursively extract names from nested sub-steps
    for sub_step in step.get("subSteps", []):
        sub_step_names.update(extract_sub_steps(sub_step))
    
    return sub_step_names

def fill_attack_track_name_to_categories_map():
    for filename in os.listdir(ATTACK_TRACKS_DIR):
        filepath = os.path.join(ATTACK_TRACKS_DIR, filename)
        if filepath.endswith('.json'):
            with open(filepath, 'r') as file:
                data = json.load(file)
                attack_track_name = data["metadata"]["name"]

                sub_step_names = set()
                sub_step_names.add(data["spec"]["data"]["name"])
                for step in data["spec"]["data"]["subSteps"]:
                    sub_step_names.update(extract_sub_steps(step))
                
                ATTACK_TRACKS_DICT[attack_track_name] = sub_step_names

# validate that if control has attack track attribute, it is a valid attack track and category
def validate_attack_track_attributes(control):
     if "attributes" in control and "attackTracks" in control["attributes"]:
        for track in control["attributes"]["attackTracks"]:
            assert track["attackTrack"] in ATTACK_TRACKS_DICT, f'Invalid attackTrack "{track["attackTrack"]}" in {control.get("controlID")}'
            for category in track.get("categories", []):
                assert category in ATTACK_TRACKS_DICT[track["attackTrack"]], f'Invalid category "{category}" for attackTrack "{track["attackTrack"]}" in {control.get("controlID")}'


# Test that each rule name in a control file has a corresponding rule file in the "rules" directory
def validate_controls():
    control_files = os.listdir(CONTROLS_DIR)
    control_ids = set()
    for control_file in control_files:
        if control_file.endswith('.json'):
            with open(os.path.join(CONTROLS_DIR, control_file), "r") as f:
                control = json.load(f)
                # validate control ID is unique
                control_id = control.get("controlID")
                assert control_id not in control_ids, f"Duplicate control ID {control_id} found in control file {control_file}"
                control_ids.add(control_id)
                # validate all rules in control exist
                for rule_name in control["rulesNames"]:
                    if rule_name in RULES_CHECKED:
                        continue
                    else:
                        assert rule_name in RULENAME_TO_RULE_DIR, f"Rule {rule_name} does not exist"
                        rule_dir = RULENAME_TO_RULE_DIR[rule_name]
                        rule_file = os.path.join(RULES_DIR, rule_dir, "rule.metadata.json")
                        assert os.path.exists(rule_file), f"Rule file {rule_file} does not exist"
                        # If there is another rule with same name as this rule with "-v1" at the end - don't validate it
                        if not os.path.exists(os.path.join(RULES_DIR, rule_dir + "-v1")):
                            validate_tests_dir_for_rule(rule_dir)
                        RULES_CHECKED.add(rule_name)
                validate_control_scanning_scope(control=control)
                validate_attack_track_attributes(control=control)


# Test that each rule directory in the "rules" directory has a non-empty "tests" subdirectory
def validate_tests_dir_for_rule(rule_dir):
        tests_dir = os.path.join(RULES_DIR, rule_dir, "test")
        # TODO: Uncomment the assert statements below once all rules have tests
        # for now, just print a message
        if not os.path.isdir(tests_dir):
            print(f"Rule '{rule_dir}' does not have tests")
        # assert os.path.isdir(tests_dir), f"Tests directory {tests_dir} does not exist"
        # assert len(os.listdir(tests_dir)) > 0, f"Tests directory {tests_dir} is empty"

def fill_controlID_to_filename_map():
    for filename in os.listdir(CONTROLS_DIR):
        # Load the JSON files
        if filename.endswith('.json'):
            with open(os.path.join(CONTROLS_DIR, filename)) as f1:
                cntl = json.load(f1)
                CONTROLID_TO_FILENAME[cntl['controlID']] = filename

def fill_rulename_to_rule_dir():
    for rule_dir in os.listdir(RULES_DIR):
        if ignore_file(rule_dir):
            continue
        if os.path.exists(os.path.join(RULES_DIR, rule_dir, "rule.metadata.json")):
            with open(os.path.join(RULES_DIR, rule_dir, "rule.metadata.json")) as f1:
                rule = json.load(f1)
                RULENAME_TO_RULE_DIR[rule['name']] = rule_dir

def validate_rules():
    for rule_dir_name in os.listdir(RULES_DIR):
        rule_dir = os.path.join(RULES_DIR, rule_dir_name)
        if not os.path.isdir(rule_dir) or rule_dir_name.startswith("."):
            continue
        
        rule_file_path = os.path.join(RULES_DIR, rule_dir_name, "rule.metadata.json")
        assert os.path.exists(rule_file_path), f"No rule.metadata.json file in {rule_dir_name}"
        with open(rule_file_path) as rule_file:
            data = json.load(rule_file)
            assert data["name"] in RULES_CHECKED, f"rule {data['name']} is not used by any control"


if __name__ == "__main__":
    fill_rulename_to_rule_dir()
    fill_controlID_to_filename_map()
    fill_attack_track_name_to_categories_map()
    validate_controls_in_framework()
    validate_controls()
    validate_rules()

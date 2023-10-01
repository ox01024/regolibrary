package armo_builtins

import future.keywords.in

# returns subjects with cluster admin role
deny[msga] {
	subjectVector := input[_]

	role := subjectVector.relatedObjects[i]
	endswith(role.kind, "Role")

	rolebinding := subjectVector.relatedObjects[j]
	endswith(rolebinding.kind, "Binding")

	rule := role.rules[p]
	subject := rolebinding.subjects[k]
	is_same_subjects(subjectVector, subject)

	# check only cluster-admin role and only clusterrolebinding
	role.metadata.name == "cluster-admin"
	rolebinding.kind == "ClusterRoleBinding"

	rule_path := sprintf("relatedObjects[%d].rules[%d]", [i, p])

	verbs := ["*"]
	verb_path := [sprintf("%s.verbs[%d]", [rule_path, l]) | verb = rule.verbs[l]; verb in verbs]
	count(verb_path) > 0

	api_groups := ["*", ""]
	api_groups_path := [sprintf("%s.apiGroups[%d]", [rule_path, a]) | apiGroup = rule.apiGroups[a]; apiGroup in api_groups]
	count(api_groups_path) > 0

	resources := ["*"]
	resources_path := [sprintf("%s.resources[%d]", [rule_path, l]) | resource = rule.resources[l]; resource in resources]
	count(resources_path) > 0

	path := array.concat(resources_path, verb_path)
	path2 := array.concat(path, api_groups_path)
	finalpath := array.concat(path2, [
		sprintf("relatedObjects[%d].subjects[%d]", [j, k]),
		sprintf("relatedObjects[%d].roleRef.name", [j]),
	])

	msga := {
		"alertMessage": sprintf("Subject: %s-%s is bound to cluster-admin role", [subjectVector.kind, subjectVector.name]),
		"alertScore": 3,
		"fixPaths": [],
		"deletePaths": finalpath,
		"failedPaths": finalpath,
		"packagename": "armo_builtins",
		"alertObject": {
			"k8sApiObjects": [],
			"externalObjects": subjectVector,
		},
	}
}

# for service accounts
is_same_subjects(subjectVector, subject) {
	subjectVector.kind == subject.kind
	subjectVector.name == subject.name
	subjectVector.namespace == subject.namespace
}

# for users/ groups
is_same_subjects(subjectVector, subject) {
	subjectVector.kind == subject.kind
	subjectVector.name == subject.name
	subjectVector.apiGroup == subject.apiGroup
}

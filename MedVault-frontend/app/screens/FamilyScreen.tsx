import { useState } from "react";
import {
  Alert,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

// Import actual assets
import { SafeAreaView } from "react-native-safe-area-context";
import defaultFemaleAvatar from "../assets/avatars/default-female.png";
import defaultAvatar from "../assets/avatars/default-male.png";

interface FamilyMember {
  id: string;
  name: string;
  dateOfBirth: string;
  gender: "male" | "female" | "other";
  relation: string;
  bloodGroup: string;
  allergies: string[];
  chronicConditions: string[];
  avatar?: string;
}

export default function FamilyScreen() {
  const [members, setMembers] = useState<FamilyMember[]>([
    {
      id: "1",
      name: "John Doe",
      dateOfBirth: "1990-01-15",
      gender: "male",
      relation: "Self",
      bloodGroup: "O+",
      allergies: ["Penicillin"],
      chronicConditions: ["Hypertension"],
    },
    {
      id: "2",
      name: "Jane Doe",
      dateOfBirth: "1992-05-22",
      gender: "female",
      relation: "Spouse",
      bloodGroup: "A+",
      allergies: [],
      chronicConditions: [],
    },
  ]);

  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMember, setEditingMember] = useState<FamilyMember | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    dateOfBirth: "",
    gender: "male" as "male" | "female" | "other",
    relation: "",
    bloodGroup: "",
    allergies: "",
    chronicConditions: "",
  });

  const resetForm = () => {
    setFormData({
      name: "",
      dateOfBirth: "",
      gender: "male",
      relation: "",
      bloodGroup: "",
      allergies: "",
      chronicConditions: "",
    });
    setEditingMember(null);
  };

  const handleAddMember = () => {
    setShowAddForm(true);
    resetForm();
  };

  const handleEditMember = (member: FamilyMember) => {
    setEditingMember(member);
    setFormData({
      name: member.name,
      dateOfBirth: member.dateOfBirth,
      gender: member.gender,
      relation: member.relation,
      bloodGroup: member.bloodGroup,
      allergies: member.allergies.join(", "),
      chronicConditions: member.chronicConditions.join(", "),
    });
    setShowAddForm(true);
  };

  const handleSaveMember = () => {
    if (!formData.name || !formData.relation) {
      Alert.alert("Error", "Please fill in all required fields");
      return;
    }

    const newMember: FamilyMember = {
      id: editingMember?.id || Date.now().toString(),
      name: formData.name,
      dateOfBirth: formData.dateOfBirth,
      gender: formData.gender,
      relation: formData.relation,
      bloodGroup: formData.bloodGroup,
      allergies: formData.allergies
        .split(",")
        .map((a) => a.trim())
        .filter((a) => a),
      chronicConditions: formData.chronicConditions
        .split(",")
        .map((c) => c.trim())
        .filter((c) => c),
    };

    if (editingMember) {
      setMembers(
        members.map((m) => (m.id === editingMember.id ? newMember : m)),
      );
    } else {
      setMembers([...members, newMember]);
    }

    setShowAddForm(false);
    resetForm();
  };

  const handleDeleteMember = (memberId: string) => {
    Alert.alert(
      "Delete Member",
      "Are you sure you want to delete this family member?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => {
            setMembers(members.filter((m) => m.id !== memberId));
          },
        },
      ],
    );
  };

  const renderMember = (member: FamilyMember) => (
    <View key={member.id} style={styles.memberCard}>
      <View style={styles.memberHeader}>
        <View style={styles.avatar}>
          <Image
            source={
              member.gender === "female" ? defaultFemaleAvatar : defaultAvatar
            }
            style={styles.avatarImage}
          />
        </View>
        <View style={styles.memberInfo}>
          <Text style={styles.memberName}>{member.name}</Text>
          <Text style={styles.memberRelation}>{member.relation}</Text>
          <Text style={styles.memberDetails}>
            {member.gender} • {member.bloodGroup} • {member.dateOfBirth}
          </Text>
        </View>
        <Pressable
          style={styles.moreButton}
          onPress={() => handleEditMember(member)}
        >
          <Text style={styles.moreButtonText}>⋮</Text>
        </Pressable>
      </View>

      {(member.allergies.length > 0 || member.chronicConditions.length > 0) && (
        <View style={styles.healthInfo}>
          {member.allergies.length > 0 && (
            <View style={styles.infoSection}>
              <Text style={styles.infoLabel}>Allergies:</Text>
              <Text style={styles.infoValue}>
                {member.allergies.join(", ")}
              </Text>
            </View>
          )}
          {member.chronicConditions.length > 0 && (
            <View style={styles.infoSection}>
              <Text style={styles.infoLabel}>Chronic Conditions:</Text>
              <Text style={styles.infoValue}>
                {member.chronicConditions.join(", ")}
              </Text>
            </View>
          )}
        </View>
      )}

      <View style={styles.memberActions}>
        <Pressable
          style={styles.actionButton}
          onPress={() => handleEditMember(member)}
        >
          <Text style={styles.actionButtonText}>Edit</Text>
        </Pressable>
        <Pressable
          style={[styles.actionButton, styles.deleteButton]}
          onPress={() => handleDeleteMember(member.id)}
        >
          <Text style={[styles.actionButtonText, styles.deleteButtonText]}>
            Delete
          </Text>
        </Pressable>
      </View>
    </View>
  );

  if (showAddForm) {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView>
          <View style={styles.header}>
            <Pressable onPress={() => setShowAddForm(false)}>
              <Text style={styles.backButton}>← Back</Text>
            </Pressable>
            <Text style={styles.title}>
              {editingMember ? "Edit Member" : "Add Family Member"}
            </Text>
          </View>

          <View style={styles.form}>
            <Text style={styles.label}>Name *</Text>
            <TextInput
              style={styles.input}
              value={formData.name}
              onChangeText={(value) =>
                setFormData({ ...formData, name: value })
              }
              placeholder="Enter name"
            />

            <Text style={styles.label}>Date of Birth</Text>
            <TextInput
              style={styles.input}
              value={formData.dateOfBirth}
              onChangeText={(value) =>
                setFormData({ ...formData, dateOfBirth: value })
              }
              placeholder="YYYY-MM-DD"
            />

            <Text style={styles.label}>Gender</Text>
            <View style={styles.genderOptions}>
              {(["male", "female", "other"] as const).map((gender) => (
                <Pressable
                  key={gender}
                  style={[
                    styles.genderOption,
                    formData.gender === gender && styles.genderOptionSelected,
                  ]}
                  onPress={() => setFormData({ ...formData, gender })}
                >
                  <Text
                    style={[
                      styles.genderText,
                      formData.gender === gender && styles.genderTextSelected,
                    ]}
                  >
                    {gender.charAt(0).toUpperCase() + gender.slice(1)}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>Relation *</Text>
            <TextInput
              style={styles.input}
              value={formData.relation}
              onChangeText={(value) =>
                setFormData({ ...formData, relation: value })
              }
              placeholder="e.g., Self, Spouse, Son, Daughter"
            />

            <Text style={styles.label}>Blood Group</Text>
            <TextInput
              style={styles.input}
              value={formData.bloodGroup}
              onChangeText={(value) =>
                setFormData({ ...formData, bloodGroup: value })
              }
              placeholder="e.g., O+, A-, B+"
            />

            <Text style={styles.label}>Allergies (comma separated)</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              value={formData.allergies}
              onChangeText={(value) =>
                setFormData({ ...formData, allergies: value })
              }
              placeholder="e.g., Penicillin, Peanuts, Dust"
              multiline
            />

            <Text style={styles.label}>
              Chronic Conditions (comma separated)
            </Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              value={formData.chronicConditions}
              onChangeText={(value) =>
                setFormData({ ...formData, chronicConditions: value })
              }
              placeholder="e.g., Diabetes, Hypertension, Asthma"
              multiline
            />

            <Pressable style={styles.saveButton} onPress={handleSaveMember}>
              <Text style={styles.saveButtonText}>
                {editingMember ? "Update Member" : "Add Member"}
              </Text>
            </Pressable>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Family Members</Text>
        <Pressable style={styles.addButton} onPress={handleAddMember}>
          <Text style={styles.addButtonText}>+ Add Member</Text>
        </Pressable>
      </View>

      <ScrollView style={styles.content}>
        {members.map((member) => renderMember(member))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F9FAFB",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 24,
    paddingBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1F2937",
  },
  backButton: {
    fontSize: 16,
    color: "#2563EB",
    fontWeight: "600",
  },
  addButton: {
    backgroundColor: "#2563EB",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  addButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
  },
  memberCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  memberHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: "#E5E7EB",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
  },
  avatarImage: {
    width: 40,
    height: 40,
    borderRadius: 20,
  },
  avatarText: {
    fontSize: 18,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  memberInfo: {
    flex: 1,
  },
  memberName: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1F2937",
    marginBottom: 2,
  },
  memberRelation: {
    fontSize: 14,
    color: "#6B7280",
    marginBottom: 2,
  },
  memberDetails: {
    fontSize: 12,
    color: "#9CA3AF",
  },
  moreButton: {
    padding: 8,
  },
  moreButtonText: {
    fontSize: 16,
    color: "#6B7280",
  },
  healthInfo: {
    marginBottom: 12,
  },
  infoSection: {
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: "#374151",
    marginBottom: 2,
  },
  infoValue: {
    fontSize: 12,
    color: "#6B7280",
  },
  memberActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
  },
  actionButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    marginLeft: 8,
  },
  deleteButton: {
    backgroundColor: "#FEE2E2",
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#2563EB",
  },
  deleteButtonText: {
    color: "#DC2626",
  },
  form: {
    padding: 24,
  },
  label: {
    fontSize: 16,
    fontWeight: "600",
    color: "#374151",
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    backgroundColor: "#FFFFFF",
    marginBottom: 16,
  },
  textArea: {
    height: 80,
    textAlignVertical: "top",
  },
  genderOptions: {
    flexDirection: "row",
    marginBottom: 16,
  },
  genderOption: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#D1D5DB",
    alignItems: "center",
    marginRight: 8,
  },
  genderOptionSelected: {
    backgroundColor: "#2563EB",
    borderColor: "#2563EB",
  },
  genderText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#6B7280",
  },
  genderTextSelected: {
    color: "#FFFFFF",
  },
  saveButton: {
    backgroundColor: "#2563EB",
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 16,
  },
  saveButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
});

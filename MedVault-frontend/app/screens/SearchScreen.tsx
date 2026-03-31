import { useState } from "react";
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
interface SearchResult {
  id: string;
  type: "medicine" | "prescription" | "member";
  title: string;
  subtitle?: string;
  description?: string;
  memberName?: string;
  date?: string;
}

export default function SearchScreen() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Mock data - in real app, this would come from API
  const mockResults: SearchResult[] = [
    {
      id: "1",
      type: "medicine",
      title: "Paracetamol",
      subtitle: "Pain reliever",
      description: "Used to treat mild to moderate pain and fever",
    },
    {
      id: "2",
      type: "prescription",
      title: "Hypertension Treatment",
      subtitle: "Dr. Smith - City Hospital",
      memberName: "John Doe",
      date: "2025-01-15",
      description: "Lisinopril 10mg, Amlodipine 5mg",
    },
    {
      id: "3",
      type: "member",
      title: "John Doe",
      subtitle: "Self - 35 years",
      description: "Blood Group: O+, Allergies: Penicillin",
    },
    {
      id: "4",
      type: "medicine",
      title: "Amoxicillin",
      subtitle: "Antibiotic",
      description: "Used to treat bacterial infections",
    },
    {
      id: "5",
      type: "prescription",
      title: "Common Cold",
      subtitle: "Dr. Johnson - Medical Center",
      memberName: "Tommy Doe",
      date: "2025-01-12",
      description: "Amoxicillin 250mg, Paracetamol 500mg",
    },
  ];

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    setIsSearching(true);

    // Simulate search delay
    setTimeout(() => {
      if (query.trim() === "") {
        setSearchResults([]);
      } else {
        const filtered = mockResults.filter(
          (result) =>
            result.title.toLowerCase().includes(query.toLowerCase()) ||
            result.subtitle?.toLowerCase().includes(query.toLowerCase()) ||
            result.description?.toLowerCase().includes(query.toLowerCase()) ||
            result.memberName?.toLowerCase().includes(query.toLowerCase()),
        );
        setSearchResults(filtered);
      }
      setIsSearching(false);
    }, 300);
  };

  const renderSearchResult = ({ item }: { item: SearchResult }) => (
    <Pressable style={styles.resultCard}>
      <View style={styles.resultHeader}>
        <View style={styles.resultTypeContainer}>
          <Text style={styles.resultType}>
            {item.type.charAt(0).toUpperCase() + item.type.slice(1)}
          </Text>
        </View>
        <Text style={styles.resultTitle}>{item.title}</Text>
      </View>

      {item.subtitle && (
        <Text style={styles.resultSubtitle}>{item.subtitle}</Text>
      )}

      {item.description && (
        <Text style={styles.resultDescription}>{item.description}</Text>
      )}

      {item.memberName && (
        <Text style={styles.memberInfo}>Member: {item.memberName}</Text>
      )}

      {item.date && <Text style={styles.dateInfo}>Date: {item.date}</Text>}
    </Pressable>
  );

  const renderEmptyState = () => (
    <View style={styles.emptyState}>
      <Text style={styles.emptyIcon}>🔍</Text>
      <Text style={styles.emptyTitle}>No results found</Text>
      <Text style={styles.emptySubtitle}>
        Try searching for medicines, prescriptions, or family members
      </Text>
    </View>
  );

  const renderSuggestions = () => (
    <View style={styles.suggestionsContainer}>
      <Text style={styles.suggestionsTitle}>Popular Searches</Text>
      <View style={styles.suggestionTags}>
        {[
          "Paracetamol",
          "Hypertension",
          "Antibiotics",
          "John Doe",
          "Vitamins",
        ].map((tag) => (
          <Pressable
            key={tag}
            style={styles.suggestionTag}
            onPress={() => handleSearch(tag)}
          >
            <Text style={styles.suggestionText}>{tag}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Search</Text>
        <Text style={styles.subtitle}>
          Find medicines, prescriptions, and more
        </Text>
      </View>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search medicines, prescriptions, members..."
          placeholderTextColor="#9CA3AF"
          value={searchQuery}
          onChangeText={handleSearch}
        />
        <Pressable style={styles.voiceButton}>
          <Text style={styles.voiceIcon}>🎤</Text>
        </Pressable>
      </View>

      {searchQuery.trim() === "" && !isSearching ? (
        renderSuggestions()
      ) : (
        <FlatList
          data={searchResults}
          renderItem={renderSearchResult}
          keyExtractor={(item) => item.id}
          ListEmptyComponent={!isSearching ? renderEmptyState : null}
          contentContainerStyle={styles.resultsList}
          showsVerticalScrollIndicator={false}
        />
      )}

      {isSearching && (
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Searching...</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F9FAFB",
  },
  header: {
    padding: 24,
    paddingBottom: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1F2937",
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: "#6B7280",
  },
  searchContainer: {
    flexDirection: "row",
    paddingHorizontal: 24,
    marginBottom: 16,
  },
  searchInput: {
    flex: 1,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    marginRight: 12,
  },
  voiceButton: {
    width: 48,
    height: 48,
    backgroundColor: "#2563EB",
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
  },
  voiceIcon: {
    fontSize: 20,
  },
  suggestionsContainer: {
    paddingHorizontal: 24,
  },
  suggestionsTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1F2937",
    marginBottom: 12,
  },
  suggestionTags: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  suggestionTag: {
    backgroundColor: "#FFFFFF",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },
  suggestionText: {
    fontSize: 14,
    color: "#374151",
  },
  resultsList: {
    paddingHorizontal: 24,
    paddingBottom: 24,
  },
  resultCard: {
    backgroundColor: "#FFFFFF",
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },
  resultHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  resultTypeContainer: {
    backgroundColor: "#F3F4F6",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    marginRight: 8,
  },
  resultType: {
    fontSize: 10,
    fontWeight: "600",
    color: "#6B7280",
  },
  resultTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1F2937",
    flex: 1,
  },
  resultSubtitle: {
    fontSize: 14,
    color: "#2563EB",
    marginBottom: 4,
  },
  resultDescription: {
    fontSize: 14,
    color: "#6B7280",
    marginBottom: 8,
  },
  memberInfo: {
    fontSize: 12,
    color: "#9CA3AF",
    marginBottom: 2,
  },
  dateInfo: {
    fontSize: 12,
    color: "#9CA3AF",
  },
  emptyState: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 24,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1F2937",
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: "#6B7280",
    textAlign: "center",
  },
  loadingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  loadingText: {
    fontSize: 16,
    color: "#6B7280",
  },
});

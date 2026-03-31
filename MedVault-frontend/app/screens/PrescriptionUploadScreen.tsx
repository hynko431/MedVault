import { useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
export default function PrescriptionUploadScreen() {
  const [uploadStep, setUploadStep] = useState<
    "camera" | "preview" | "processing" | "review"
  >("camera");
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const [extractedData, setExtractedData] = useState({
    doctorName: "",
    hospitalName: "",
    diagnosis: "",
    medicines: [] as Array<{
      name: string;
      dosage: string;
      frequency: string;
      duration: string;
    }>,
  });

  const handleCameraCapture = () => {
    // In real app, this would open camera
    Alert.alert("Camera", "Camera functionality would be implemented here");
    // Mock adding images
    setSelectedImages(["mock_image_1", "mock_image_2"]);
    setUploadStep("preview");
  };

  const handleGallerySelect = () => {
    // In real app, this would open gallery
    Alert.alert("Gallery", "Gallery functionality would be implemented here");
    // Mock adding images
    setSelectedImages(["mock_gallery_image"]);
    setUploadStep("preview");
  };

  const handleRetakePhotos = () => {
    setSelectedImages([]);
    setUploadStep("camera");
  };

  const handleProcessOCR = () => {
    setUploadStep("processing");
    // Simulate OCR processing
    setTimeout(() => {
      setExtractedData({
        doctorName: "Dr. Smith",
        hospitalName: "City Hospital",
        diagnosis: "Hypertension",
        medicines: [
          {
            name: "Lisinopril",
            dosage: "10mg",
            frequency: "Once daily",
            duration: "30 days",
          },
          {
            name: "Amlodipine",
            dosage: "5mg",
            frequency: "Twice daily",
            duration: "30 days",
          },
        ],
      });
      setUploadStep("review");
    }, 3000);
  };

  const handleSavePrescription = () => {
    // In real app, this would save to backend
    Alert.alert("Success", "Prescription saved successfully!");
    // Navigate back to dashboard
  };

  const handleEditField = (field: string, value: string) => {
    setExtractedData({
      ...extractedData,
      [field]: value,
    });
  };

  const renderCameraStep = () => (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Upload Prescription</Text>
        <Text style={styles.subtitle}>Take a photo or select from gallery</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.uploadOptions}>
          <Pressable style={styles.uploadOption} onPress={handleCameraCapture}>
            <Text style={styles.uploadIcon}>📸</Text>
            <Text style={styles.uploadTitle}>Take Photo</Text>
            <Text style={styles.uploadSubtitle}>
              Use camera to capture prescription
            </Text>
          </Pressable>

          <Pressable style={styles.uploadOption} onPress={handleGallerySelect}>
            <Text style={styles.uploadIcon}>🖼️</Text>
            <Text style={styles.uploadTitle}>Select from Gallery</Text>
            <Text style={styles.uploadSubtitle}>
              Choose existing prescription image
            </Text>
          </Pressable>
        </View>

        <View style={styles.tipsContainer}>
          <Text style={styles.tipsTitle}>Tips for best results:</Text>
          <Text style={styles.tip}>• Ensure good lighting</Text>
          <Text style={styles.tip}>• Place prescription on flat surface</Text>
          <Text style={styles.tip}>• Avoid shadows and glare</Text>
          <Text style={styles.tip}>• Capture entire prescription</Text>
          <Text style={styles.tip}>• Make sure text is clearly visible</Text>
        </View>
      </View>
    </SafeAreaView>
  );

  const renderPreviewStep = () => (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Review Images</Text>
        <Text style={styles.subtitle}>
          Selected {selectedImages.length} image(s)
        </Text>
      </View>

      <ScrollView style={styles.content}>
        <View style={styles.imagePreviewContainer}>
          {selectedImages.map((image, index) => (
            <View key={index} style={styles.imagePreview}>
              <Text style={styles.imagePlaceholder}>
                📄 Prescription Image {index + 1}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.actionButtons}>
          <Pressable
            style={styles.secondaryButton}
            onPress={handleRetakePhotos}
          >
            <Text style={styles.secondaryButtonText}>Retake Photos</Text>
          </Pressable>
          <Pressable style={styles.primaryButton} onPress={handleProcessOCR}>
            <Text style={styles.primaryButtonText}>Process with OCR</Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );

  const renderProcessingStep = () => (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.processingContainer}>
          <Text style={styles.processingTitle}>Processing with AI</Text>
          <Text style={styles.processingSubtitle}>
            Extracting text and analyzing prescription...
          </Text>

          <View style={styles.loadingAnimation}>
            <Text style={styles.loadingDot}>•</Text>
            <Text style={styles.loadingDot}>•</Text>
            <Text style={styles.loadingDot}>•</Text>
          </View>

          <Text style={styles.processingNote}>
            This usually takes 2-5 seconds
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );

  const renderReviewStep = () => (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        <View style={styles.header}>
          <Text style={styles.title}>Review Extracted Data</Text>
          <Text style={styles.subtitle}>Please verify and edit if needed</Text>
        </View>

        <View style={styles.content}>
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Doctor Information</Text>
            <View style={styles.fieldContainer}>
              <Text style={styles.fieldLabel}>Doctor Name</Text>
              <Pressable style={styles.fieldValue}>
                <Text style={styles.fieldText}>
                  {extractedData.doctorName || "Not detected"}
                </Text>
              </Pressable>
            </View>
            <View style={styles.fieldContainer}>
              <Text style={styles.fieldLabel}>Hospital/Clinic</Text>
              <Pressable style={styles.fieldValue}>
                <Text style={styles.fieldText}>
                  {extractedData.hospitalName || "Not detected"}
                </Text>
              </Pressable>
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Medical Information</Text>
            <View style={styles.fieldContainer}>
              <Text style={styles.fieldLabel}>Diagnosis</Text>
              <Pressable style={styles.fieldValue}>
                <Text style={styles.fieldText}>
                  {extractedData.diagnosis || "Not detected"}
                </Text>
              </Pressable>
            </View>
          </View>

          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              Medicines ({extractedData.medicines.length})
            </Text>
            {extractedData.medicines.map((medicine, index) => (
              <View key={index} style={styles.medicineCard}>
                <Text style={styles.medicineName}>{medicine.name}</Text>
                <View style={styles.medicineDetails}>
                  <Text style={styles.medicineDetail}>
                    Dosage: {medicine.dosage}
                  </Text>
                  <Text style={styles.medicineDetail}>
                    Frequency: {medicine.frequency}
                  </Text>
                  <Text style={styles.medicineDetail}>
                    Duration: {medicine.duration}
                  </Text>
                </View>
              </View>
            ))}
          </View>

          <View style={styles.actionButtons}>
            <Pressable
              style={styles.secondaryButton}
              onPress={() => setUploadStep("preview")}
            >
              <Text style={styles.secondaryButtonText}>Back to Images</Text>
            </Pressable>
            <Pressable
              style={styles.primaryButton}
              onPress={handleSavePrescription}
            >
              <Text style={styles.primaryButtonText}>Save Prescription</Text>
            </Pressable>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );

  switch (uploadStep) {
    case "camera":
      return renderCameraStep();
    case "preview":
      return renderPreviewStep();
    case "processing":
      return renderProcessingStep();
    case "review":
      return renderReviewStep();
    default:
      return renderCameraStep();
  }
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
  content: {
    flex: 1,
    paddingHorizontal: 24,
  },
  uploadOptions: {
    gap: 16,
    marginBottom: 32,
  },
  uploadOption: {
    backgroundColor: "#FFFFFF",
    padding: 24,
    borderRadius: 12,
    alignItems: "center",
  },
  uploadIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  uploadTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1F2937",
    marginBottom: 4,
  },
  uploadSubtitle: {
    fontSize: 14,
    color: "#6B7280",
    textAlign: "center",
  },
  tipsContainer: {
    backgroundColor: "#F3F4F6",
    padding: 16,
    borderRadius: 12,
  },
  tipsTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1F2937",
    marginBottom: 12,
  },
  tip: {
    fontSize: 14,
    color: "#4B5563",
    marginBottom: 4,
  },
  imagePreviewContainer: {
    marginBottom: 24,
  },
  imagePreview: {
    backgroundColor: "#FFFFFF",
    padding: 16,
    borderRadius: 12,
    alignItems: "center",
    marginBottom: 12,
  },
  imagePlaceholder: {
    fontSize: 16,
    color: "#6B7280",
  },
  actionButtons: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: "#2563EB",
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  primaryButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: "#F3F4F6",
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: "center",
  },
  secondaryButtonText: {
    color: "#6B7280",
    fontSize: 16,
    fontWeight: "600",
  },
  processingContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  processingTitle: {
    fontSize: 24,
    fontWeight: "700",
    color: "#1F2937",
    marginBottom: 8,
  },
  processingSubtitle: {
    fontSize: 16,
    color: "#6B7280",
    textAlign: "center",
    marginBottom: 32,
  },
  loadingAnimation: {
    flexDirection: "row",
    marginBottom: 16,
  },
  loadingDot: {
    fontSize: 24,
    color: "#2563EB",
    marginHorizontal: 4,
  },
  processingNote: {
    fontSize: 14,
    color: "#9CA3AF",
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#1F2937",
    marginBottom: 16,
  },
  fieldContainer: {
    marginBottom: 16,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: "600",
    color: "#374151",
    marginBottom: 8,
  },
  fieldValue: {
    backgroundColor: "#FFFFFF",
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#D1D5DB",
  },
  fieldText: {
    fontSize: 16,
    color: "#1F2937",
  },
  medicineCard: {
    backgroundColor: "#FFFFFF",
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    marginBottom: 12,
  },
  medicineName: {
    fontSize: 16,
    fontWeight: "600",
    color: "#1F2937",
    marginBottom: 8,
  },
  medicineDetails: {
    gap: 4,
  },
  medicineDetail: {
    fontSize: 14,
    color: "#6B7280",
  },
});

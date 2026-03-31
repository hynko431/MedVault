import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

interface TermsScreenProps {
  onBack: () => void;
}

export default function TermsScreen({ onBack }: TermsScreenProps) {
  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Terms of Service</Text>
          <Text style={styles.subtitle}>Last updated: January 2025</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>1. Acceptance of Terms</Text>
          <Text style={styles.sectionText}>
            By accessing and using MedVault, you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>2. Description of Service</Text>
          <Text style={styles.sectionText}>
            MedVault is a digital health management platform that allows users to store, organize, and manage medical records, prescriptions, and health-related information. The service is provided on an "as is" basis.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>3. User Responsibilities</Text>
          <Text style={styles.sectionText}>
            As a user, you are responsible for:
          </Text>
          <Text style={styles.bulletText}>
            • Maintaining the accuracy of your medical information
          </Text>
          <Text style={styles.bulletText}>
            • Keeping your login credentials secure
          </Text>
          <Text style={styles.bulletText}>
            • Not sharing your account with unauthorized individuals
          </Text>
          <Text style={styles.bulletText}>
            • Reporting any inaccuracies in your medical records
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>4. Medical Information Disclaimer</Text>
          <Text style={styles.sectionText}>
            MedVault does not provide medical advice, diagnosis, or treatment. The information stored in our app should not be used as a substitute for professional medical consultation. Always consult with qualified healthcare providers for medical decisions.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>5. Privacy and Data Security</Text>
          <Text style={styles.sectionText}>
            We are committed to protecting your privacy. All medical data is encrypted and stored securely. We do not sell, rent, or share your personal health information with third parties without your explicit consent, except as required by law.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>6. Limitation of Liability</Text>
          <Text style={styles.sectionText}>
            MedVault shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses, resulting from your use of the service.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>7. Termination</Text>
          <Text style={styles.sectionText}>
            We may terminate or suspend your account immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach the Terms.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>8. Changes to Terms</Text>
          <Text style={styles.sectionText}>
            We reserve the right to modify or replace these Terms at any time. If a revision is material, we will provide at least 30 days notice prior to any new terms taking effect.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>9. Contact Information</Text>
          <Text style={styles.sectionText}>
            If you have any questions about these Terms of Service, please contact us at:
          </Text>
          <Text style={styles.contactText}>
            Email: legal@medvault.app
          </Text>
          <Text style={styles.contactText}>
            Address: MedVault Inc., Health Tech District, CA 94102
          </Text>
        </View>
      </View>

      <View style={styles.footer}>
        <Pressable style={styles.backButton} onPress={onBack}>
          <Text style={styles.backButtonText}>Back to Disclaimer</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1000,
  },
  content: {
    padding: 24,
    paddingBottom: 32,
  },
  header: {
    marginBottom: 32,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 12,
  },
  sectionText: {
    fontSize: 14,
    color: '#4B5563',
    lineHeight: 20,
    marginBottom: 8,
  },
  bulletText: {
    fontSize: 14,
    color: '#4B5563',
    lineHeight: 20,
    marginLeft: 16,
    marginBottom: 4,
  },
  contactText: {
    fontSize: 14,
    color: '#2563EB',
    fontWeight: '600',
    marginBottom: 4,
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 24,
    backgroundColor: '#FFFFFF',
  },
  backButton: {
    backgroundColor: '#F3F4F6',
    paddingVertical: 16,
    borderRadius: 30,
  },
  backButtonText: {
    color: '#6B7280',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
});

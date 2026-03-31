import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

interface PrivacyScreenProps {
  onBack: () => void;
}

export default function PrivacyScreen({ onBack }: PrivacyScreenProps) {
  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Privacy Policy</Text>
          <Text style={styles.subtitle}>Last updated: January 2025</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>1. Information We Collect</Text>
          <Text style={styles.sectionText}>
            We collect information you provide directly to us, such as when you create an account, update your profile, or input medical information. This may include:
          </Text>
          <Text style={styles.bulletText}>
            • Personal identification information (name, email, phone)
          </Text>
          <Text style={styles.bulletText}>
            • Medical records and prescription information
          </Text>
          <Text style={styles.bulletText}>
            • Device information and usage data
          </Text>
          <Text style={styles.bulletText}>
            • Location data (with your explicit consent)
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>2. How We Use Your Information</Text>
          <Text style={styles.sectionText}>
            We use the information we collect to:
          </Text>
          <Text style={styles.bulletText}>
            • Provide, maintain, and improve our services
          </Text>
          <Text style={styles.bulletText}>
            • Process transactions and send related information
          </Text>
          <Text style={styles.bulletText}>
            • Send technical notices and support messages
          </Text>
          <Text style={styles.bulletText}>
            • Respond to your comments and questions
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>3. Data Security</Text>
          <Text style={styles.sectionText}>
            We implement appropriate technical and organizational measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction. These include:
          </Text>
          <Text style={styles.bulletText}>
            • End-to-end encryption for all medical data
          </Text>
          <Text style={styles.bulletText}>
            • Secure servers with regular security audits
          </Text>
          <Text style={styles.bulletText}>
            • Role-based access control for our staff
          </Text>
          <Text style={styles.bulletText}>
            • Regular backups and disaster recovery procedures
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>4. Data Sharing and Disclosure</Text>
          <Text style={styles.sectionText}>
            We do not sell, trade, or otherwise transfer your personal health information to third parties without your consent, except in the following circumstances:
          </Text>
          <Text style={styles.bulletText}>
            • With your explicit consent
          </Text>
          <Text style={styles.bulletText}>
            • To comply with legal obligations
          </Text>
          <Text style={styles.bulletText}>
            • To protect our rights, privacy, safety, or property
          </Text>
          <Text style={styles.bulletText}>
            • With trusted service providers under strict confidentiality agreements
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>5. Your Rights</Text>
          <Text style={styles.sectionText}>
            You have the right to:
          </Text>
          <Text style={styles.bulletText}>
            • Access your personal information
          </Text>
          <Text style={styles.bulletText}>
            • Correct inaccurate information
          </Text>
          <Text style={styles.bulletText}>
            • Request deletion of your data
          </Text>
          <Text style={styles.bulletText}>
            • Opt-out of non-essential communications
          </Text>
          <Text style={styles.bulletText}>
            • Export your data in a portable format
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>6. Data Retention</Text>
          <Text style={styles.sectionText}>
            We retain your personal information only as long as necessary to provide our services and comply with legal obligations. Medical records are retained according to healthcare regulations and industry standards.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>7. Children's Privacy</Text>
          <Text style={styles.sectionText}>
            Our service is not intended for children under 13. We do not knowingly collect personal information from children under 13. If you become aware that a child has provided us with personal information, please contact us.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>8. Changes to This Policy</Text>
          <Text style={styles.sectionText}>
            We may update our Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last updated" date.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>9. Contact Us</Text>
          <Text style={styles.sectionText}>
            If you have any questions about this Privacy Policy, please contact us:
          </Text>
          <Text style={styles.contactText}>
            Email: privacy@medvault.app
          </Text>
          <Text style={styles.contactText}>
            Phone: 1-800-MEDVAULT
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

import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

interface DisclaimerScreenProps {
  onAccept: () => void;
  onShowTerms: () => void;
  onShowPrivacy: () => void;
}

export default function DisclaimerScreen({ onAccept, onShowTerms, onShowPrivacy }: DisclaimerScreenProps) {
  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Welcome to MedVault</Text>
          <Text style={styles.subtitle}>Your Digital Health Companion</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>App Purpose</Text>
          <Text style={styles.sectionText}>
            MedVault is designed to help you securely store, organize, and manage your family's medical records and prescriptions. Our app provides a centralized platform for digitizing health information, making it easily accessible whenever you need it.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Medical Disclaimer</Text>
          <Text style={styles.disclaimerText}>
            <Text style={styles.bold}>IMPORTANT:</Text> MedVault is NOT a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.
          </Text>
          <Text style={styles.disclaimerText}>
            • Do not disregard professional medical advice or delay in seeking it because of something you have read on this app.
          </Text>
          <Text style={styles.disclaimerText}>
            • If you think you may have a medical emergency, call your doctor or emergency services immediately.
          </Text>
          <Text style={styles.disclaimerText}>
            • The information provided is for educational purposes only and should not be used as a basis for diagnosis or treatment.
          </Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Data Privacy</Text>
          <Text style={styles.sectionText}>
            Your health data is encrypted and stored securely. We are committed to protecting your privacy and maintaining the confidentiality of your medical information.
          </Text>
        </View>

        <View style={styles.linksContainer}>
          <Pressable style={styles.linkButton} onPress={onShowTerms}>
            <Text style={styles.linkText}>Terms of Service</Text>
          </Pressable>
          <Pressable style={styles.linkButton} onPress={onShowPrivacy}>
            <Text style={styles.linkText}>Privacy Policy</Text>
          </Pressable>
        </View>

        <View style={styles.agreementContainer}>
          <Text style={styles.agreementText}>
            By clicking "Accept & Continue", you acknowledge that you have read, understood, and agree to our Terms of Service and Privacy Policy, and you accept the medical disclaimer above.
          </Text>
        </View>
      </View>

      <View style={styles.footer}>
        <Pressable style={styles.acceptButton} onPress={onAccept}>
          <Text style={styles.acceptButtonText}>Accept & Continue</Text>
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
    alignItems: 'center',
    marginBottom: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1F2937',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 12,
  },
  sectionText: {
    fontSize: 14,
    color: '#4B5563',
    lineHeight: 20,
  },
  disclaimerText: {
    fontSize: 14,
    color: '#DC2626',
    lineHeight: 20,
    marginBottom: 8,
  },
  bold: {
    fontWeight: '700',
  },
  linksContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginVertical: 24,
  },
  linkButton: {
    paddingVertical: 12,
    paddingHorizontal: 20,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
  },
  linkText: {
    fontSize: 14,
    color: '#2563EB',
    fontWeight: '600',
  },
  agreementContainer: {
    backgroundColor: '#FEF3C7',
    padding: 16,
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#F59E0B',
  },
  agreementText: {
    fontSize: 12,
    color: '#92400E',
    lineHeight: 18,
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 24,
    backgroundColor: '#FFFFFF',
  },
  acceptButton: {
    backgroundColor: '#2563EB',
    paddingVertical: 16,
    borderRadius: 30,
  },
  acceptButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
});

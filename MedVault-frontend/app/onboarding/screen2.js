import { FileText, Globe, Sparkles } from 'lucide-react-native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

export default function OnboardingScreen2({ onNext, onBack }) {
  const features = [
    {
      Icon: FileText,
      title: 'OCR Prescription Upload',
      description: 'Scan and digitize prescriptions instantly with advanced text recognition'
    },
    {
      Icon: Sparkles,
      title: 'AI Medicine Explanations',
      description: 'Get easy-to-understand explanations about your medications powered by AI'
    },
    {
      Icon: Globe,
      title: 'Multi-language Support',
      description: 'Access the app in your preferred language for better understanding'
    }
  ];

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.content}>
        <Text style={styles.title}>Key Features</Text>
        <Text style={styles.subtitle}>
          Everything you need to manage your family's health in one place
        </Text>

        <View style={styles.featuresContainer}>
          {features.map((feature, index) => (
            <View key={index} style={styles.featureItem}>
              <View style={styles.iconContainer}>
                <feature.Icon size={24} color="#2563EB" />
              </View>
              <View style={styles.textContainer}>
                <Text style={styles.featureTitle}>{feature.title}</Text>
                <Text style={styles.featureDescription}>{feature.description}</Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      <View style={styles.footer}>
        <Pressable style={styles.primaryBtn} onPress={onNext}>
          <Text style={styles.btnText}>Continue</Text>
        </Pressable>
        <Pressable style={styles.secondaryBtn} onPress={onBack}>
          <Text style={styles.secondaryBtnText}>Back</Text>
        </Pressable>
        <View style={styles.progress}>
          <View style={[styles.bar, styles.inactiveBar]} />
          <View style={[styles.bar, styles.activeBar]} />
          <View style={[styles.bar, styles.inactiveBar]} />
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  content: {
    paddingHorizontal: 24,
    paddingVertical: 32,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 12,
    color: '#000',
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 32,
  },
  featuresContainer: {
    gap: 16,
  },
  featureItem: {
    flexDirection: 'row',
    gap: 12,
  },
  iconContainer: {
    width: 48,
    height: 48,
    backgroundColor: '#DBEAFE',
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  textContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  featureTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#000',
    marginBottom: 4,
  },
  featureDescription: {
    fontSize: 12,
    color: '#6B7280',
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 24,
  },
  primaryBtn: {
    backgroundColor: '#2563EB',
    paddingVertical: 16,
    borderRadius: 30,
    marginBottom: 12,
  },
  secondaryBtn: {
    paddingVertical: 16,
    borderRadius: 30,
    marginBottom: 16,
  },
  btnText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  secondaryBtnText: {
    color: '#6B7280',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  progress: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
  },
  bar: {
    width: 32,
    height: 4,
    borderRadius: 2,
  },
  activeBar: {
    backgroundColor: '#2563EB',
  },
  inactiveBar: {
    backgroundColor: '#D1D5DB',
  },
});

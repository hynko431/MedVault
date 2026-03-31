import { Bell, Camera } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, Text, View } from 'react-native';

export default function OnboardingScreen3({ onComplete, onBack }) {
  const [cameraPermission, setCameraPermission] = useState(false);
  const [notificationPermission, setNotificationPermission] = useState(false);

  const permissions = [
    {
      Icon: Camera,
      title: 'Camera Permission',
      description: 'Required to scan prescriptions and upload photos',
      state: cameraPermission,
      setState: setCameraPermission
    },
    {
      Icon: Bell,
      title: 'Notifications Permission',
      description: 'Get reminders for medication times and refills',
      state: notificationPermission,
      setState: setNotificationPermission
    }
  ];

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      <View style={styles.content}>
        <Text style={styles.title}>Enable Permissions</Text>
        <Text style={styles.subtitle}>
          We need a few permissions to provide you with the best experience
        </Text>

        <View style={styles.permissionsContainer}>
          {permissions.map((permission, index) => (
            <View key={index} style={styles.permissionCard}>
              <View style={styles.permissionHeader}>
                <View style={styles.iconContainer}>
                  <permission.Icon size={24} color="#2563EB" />
                </View>
                <View style={styles.textContainer}>
                  <Text style={styles.permissionTitle}>{permission.title}</Text>
                  <Text style={styles.permissionDescription}>{permission.description}</Text>
                </View>
              </View>
              <Switch
                value={permission.state}
                onValueChange={permission.setState}
                trackColor={{ false: '#D1D5DB', true: '#DBEAFE' }}
                thumbColor={permission.state ? '#2563EB' : '#6B7280'}
                style={styles.switch}
              />
            </View>
          ))}
        </View>

        <Text style={styles.notice}>
          You can change these permissions anytime in your device settings
        </Text>
      </View>

      <View style={styles.footer}>
        <Pressable style={styles.primaryBtn} onPress={onComplete}>
          <Text style={styles.btnText}>Continue to App</Text>
        </Pressable>
        <Pressable style={styles.secondaryBtn} onPress={onBack}>
          <Text style={styles.secondaryBtnText}>Back</Text>
        </Pressable>
        <View style={styles.progress}>
          <View style={[styles.bar, styles.inactiveBar]} />
          <View style={[styles.bar, styles.inactiveBar]} />
          <View style={[styles.bar, styles.activeBar]} />
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
  permissionsContainer: {
    gap: 12,
  },
  permissionCard: {
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  permissionHeader: {
    flexDirection: 'row',
    gap: 12,
    flex: 1,
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
  permissionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#000',
    marginBottom: 4,
  },
  permissionDescription: {
    fontSize: 12,
    color: '#6B7280',
  },
  switch: {
    marginLeft: 12,
  },
  notice: {
    fontSize: 11,
    color: '#9CA3AF',
    textAlign: 'center',
    marginTop: 24,
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

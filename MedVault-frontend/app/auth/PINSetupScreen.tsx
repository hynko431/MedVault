import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

interface PINSetupScreenProps {
  onPINSet?: (pin: string) => void;
}

export default function PINSetupScreen({ onPINSet }: PINSetupScreenProps) {
  const [pin, setPin] = useState(['', '', '', '']);
  const [confirmPin, setConfirmPin] = useState(['', '', '', '']);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState('');

  const handlePINChange = (value: string, index: number, isConfirm: boolean = false) => {
    if (value.length <= 1) {
      const newPIN = isConfirm ? [...confirmPin] : [...pin];
      newPIN[index] = value;
      
      if (isConfirm) {
        setConfirmPin(newPIN);
      } else {
        setPin(newPIN);
      }

      // Auto-focus next input
      if (value && index < 3) {
        // In real implementation, you'd use refs to focus next input
      }

      // Check if PIN is complete
      if (!isConfirm && newPIN.every(digit => digit.length === 1)) {
        setTimeout(() => setShowConfirm(true), 100);
      }

      // Check if confirm PIN is complete
      if (isConfirm && newPIN.every(digit => digit.length === 1)) {
        const pinString = pin.join('');
        const confirmPinString = newPIN.join('');
        
        if (pinString !== confirmPinString) {
          setError('PINs do not match. Please try again.');
          setPin(['', '', '', '']);
          setConfirmPin(['', '', '', '']);
          setShowConfirm(false);
        } else {
          if (onPINSet) {
            onPINSet(pinString);
          } else {
            // Save login state and navigate to dashboard
            AsyncStorage.setItem('isLoggedIn', 'true');
            router.replace('/(tabs)/dashboard');
          }
        }
      }
    }
  };

  const resetPIN = () => {
    setPin(['', '', '', '']);
    setConfirmPin(['', '', '', '']);
    setShowConfirm(false);
    setError('');
  };

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>
            {showConfirm ? 'Confirm PIN' : 'Set PIN'}
          </Text>
          <Text style={styles.subtitle}>
            {showConfirm 
              ? 'Re-enter your 4-digit PIN to confirm'
              : 'Create a 4-digit PIN for quick access'
            }
          </Text>
        </View>

        <View style={styles.pinContainer}>
          {(showConfirm ? confirmPin : pin).map((digit, index) => (
            <TextInput
              key={showConfirm ? `confirm-${index}` : `pin-${index}`}
              style={styles.pinInput}
              value={digit}
              onChangeText={(value) => handlePINChange(value, index, showConfirm)}
              keyboardType="number-pad"
              maxLength={1}
              textAlign="center"
              secureTextEntry
            />
          ))}
        </View>

        {error ? (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{error}</Text>
            <Pressable onPress={resetPIN}>
              <Text style={styles.retryText}>Try Again</Text>
            </Pressable>
          </View>
        ) : null}

        {!showConfirm && (
          <View style={styles.infoContainer}>
            <Text style={styles.infoTitle}>PIN Requirements:</Text>
            <Text style={styles.infoText}>• 4 digits only</Text>
            <Text style={styles.infoText}>• Easy to remember</Text>
            <Text style={styles.infoText}>• Avoid common patterns (1234, 0000)</Text>
          </View>
        )}

        {showConfirm && (
          <Pressable style={styles.backButton} onPress={resetPIN}>
            <Text style={styles.backButtonText}>Back to PIN Setup</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: 48,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 24,
  },
  pinContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 32,
  },
  pinInput: {
    width: 60,
    height: 60,
    borderWidth: 2,
    borderColor: '#D1D5DB',
    borderRadius: 12,
    fontSize: 24,
    fontWeight: '600',
    color: '#1F2937',
    backgroundColor: '#F9FAFB',
  },
  errorContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  errorText: {
    fontSize: 14,
    color: '#EF4444',
    marginBottom: 8,
    textAlign: 'center',
  },
  retryText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2563EB',
  },
  infoContainer: {
    backgroundColor: '#F3F4F6',
    padding: 16,
    borderRadius: 12,
    marginBottom: 24,
  },
  infoTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  infoText: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 4,
  },
  backButton: {
    alignItems: 'center',
  },
  backButtonText: {
    fontSize: 14,
    color: '#6B7280',
  },
});

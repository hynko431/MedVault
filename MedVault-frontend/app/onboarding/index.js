import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import OnboardingScreen1 from './screen1';
import OnboardingScreen2 from './screen2';
import OnboardingScreen3 from './screen3';

export default function OnboardingFlow({ onComplete }) {
  const [currentScreen, setCurrentScreen] = useState(1);

  const handleNext = () => {
    if (currentScreen < 3) {
      setCurrentScreen(currentScreen + 1);
    } else if (currentScreen === 3) {
      onComplete();
    }
  };

  const handleBack = () => {
    if (currentScreen > 1) {
      setCurrentScreen(currentScreen - 1);
    }
  };

  return (
    <View style={styles.container}>
      {currentScreen === 1 && <OnboardingScreen1 onNext={handleNext} />}
      {currentScreen === 2 && <OnboardingScreen2 onNext={handleNext} onBack={handleBack} />}
      {currentScreen === 3 && <OnboardingScreen3 onComplete={onComplete} onBack={handleBack} />}
    </View>
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
});

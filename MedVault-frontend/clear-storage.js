// Script to clear AsyncStorage for fresh testing
const AsyncStorage = require('@react-native-async-storage/async-storage').default;

const clearStorage = async () => {
  try {
    console.log('Clearing AsyncStorage...');
    
    // Clear all app-specific keys
    await AsyncStorage.removeItem('disclaimerAccepted');
    await AsyncStorage.removeItem('onboardingComplete');
    await AsyncStorage.removeItem('isLoggedIn');
    
    // Clear any additional keys that might exist
    const allKeys = await AsyncStorage.getAllKeys();
    const appKeys = allKeys.filter(key => 
      key.includes('disclaimer') || 
      key.includes('onboarding') || 
      key.includes('isLoggedIn') ||
      key.includes('auth') ||
      key.includes('user')
    );
    
    if (appKeys.length > 0) {
      await AsyncStorage.multiRemove(appKeys);
    }
    
    console.log('AsyncStorage cleared successfully!');
    console.log('Cleared keys:', appKeys);
    
  } catch (error) {
    console.error('Error clearing AsyncStorage:', error);
  }
};

clearStorage();

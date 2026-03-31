import { Stack } from "expo-router";

export default function AuthLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen name="AuthOptionsScreen" options={{ title: "Welcome" }} />
      <Stack.Screen name="LoginScreen" options={{ title: "Mobile Login" }} />
      <Stack.Screen name="EmailLoginScreen" options={{ title: "Email Login" }} />
      <Stack.Screen name="OTPScreen" options={{ title: "OTP Verification" }} />
      <Stack.Screen name="PINSetupScreen" options={{ title: "PIN Setup" }} />
    </Stack>
  );
}

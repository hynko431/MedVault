import { router } from "expo-router";
import React from "react";
import {
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
  SafeAreaView,
} from "react-native";
import { Mail, Phone, Chrome } from "lucide-react-native";

export default function AuthOptionsScreen() {
  const handleContinueWithMobile = () => {
    router.push("/auth/LoginScreen");
  };

  const handleContinueWithEmail = () => {
    router.push("/auth/EmailLoginScreen");
  };

  const handleGoogleLogin = () => {
    // Placeholder for Google Login logic
    console.log("Google Login pressed");
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Image
            source={require("../assets/logo.png")}
            style={styles.logo}
            resizeMode="contain"
          />
          <Text style={styles.title}>MedVault</Text>
          <Text style={styles.subtitle}>Your Secure Medical Records Vault</Text>
        </View>

        <View style={styles.optionsContainer}>
          <Pressable
            style={[styles.button, styles.mobileButton]}
            onPress={handleContinueWithMobile}
          >
            <Phone size={20} color="#FFFFFF" style={styles.buttonIcon} />
            <Text style={styles.buttonText}>Continue with Mobile</Text>
          </Pressable>

          <Pressable
            style={[styles.button, styles.emailButton]}
            onPress={handleContinueWithEmail}
          >
            <Mail size={20} color="#374151" style={styles.buttonIcon} />
            <Text style={styles.emailButtonText}>Continue with Email</Text>
          </Pressable>

          <View style={styles.dividerContainer}>
            <View style={styles.divider} />
            <Text style={styles.dividerText}>OR</Text>
            <View style={styles.divider} />
          </View>

          <Pressable
            style={[styles.button, styles.googleButton]}
            onPress={handleGoogleLogin}
          >
            <Chrome size={20} color="#EA4335" style={styles.buttonIcon} />
            <Text style={styles.googleButtonText}>Sign in with Google</Text>
          </Pressable>
        </View>

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            By continuing, you agree to our{" "}
            <Text style={styles.linkText}>Terms of Service</Text> and{" "}
            <Text style={styles.linkText}>Privacy Policy</Text>
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: "space-between",
  },
  header: {
    alignItems: "center",
    marginTop: 60,
  },
  logo: {
    width: 100,
    height: 100,
    marginBottom: 16,
  },
  title: {
    fontSize: 32,
    fontWeight: "800",
    color: "#1F2937",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: "#6B7280",
    textAlign: "center",
  },
  optionsContainer: {
    width: "100%",
    gap: 16,
  },
  button: {
    height: 56,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
    width: "100%",
  },
  mobileButton: {
    backgroundColor: "#2563EB",
  },
  emailButton: {
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#D1D5DB",
  },
  googleButton: {
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#D1D5DB",
  },
  buttonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#FFFFFF",
  },
  emailButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#374151",
  },
  googleButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#374151",
  },
  buttonIcon: {
    marginRight: 12,
  },
  dividerContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 8,
  },
  divider: {
    flex: 1,
    height: 1,
    backgroundColor: "#E5E7EB",
  },
  dividerText: {
    marginHorizontal: 16,
    color: "#9CA3AF",
    fontSize: 14,
    fontWeight: "500",
  },
  footer: {
    marginBottom: 20,
  },
  footerText: {
    fontSize: 12,
    color: "#6B7280",
    textAlign: "center",
    lineHeight: 18,
  },
  linkText: {
    color: "#2563EB",
    fontWeight: "500",
  },
});

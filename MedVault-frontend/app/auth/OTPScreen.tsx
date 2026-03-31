import AsyncStorage from "@react-native-async-storage/async-storage";
import { router, useLocalSearchParams } from "expo-router";
import { ArrowLeft } from "lucide-react-native";
import { useEffect, useState } from "react";
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

export default function OTPScreen() {
  const { mobile } = useLocalSearchParams();
  const mobileNumber = (mobile as string) || "";

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [timeLeft, setTimeLeft] = useState(30);
  const [canResend, setCanResend] = useState(false);

  /* ---------------- TIMER ---------------- */
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          setCanResend(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  /* ---------------- OTP HANDLER ---------------- */
  const handleOTPChange = async (value: string, index: number) => {
    if (value.length > 1) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // ✅ AUTO VERIFY (TEMP BYPASS)
    if (newOtp.every((d) => d !== "")) {
      setTimeout(async () => {
        // SAVE LOGIN STATE
        await AsyncStorage.setItem("isLoggedIn", "true");
        await AsyncStorage.setItem("token", "dummy-token-for-now");

        router.replace("/(tabs)/dashboard");
      }, 200);
    }
  };

  /* ---------------- RESEND ---------------- */
  const handleResendOTP = () => {
    if (!canResend) return;
    setOtp(["", "", "", "", "", ""]);
    setTimeLeft(30);
    setCanResend(false);
  };

  const formatMobileNumber = (num: string) =>
    num ? `+91 ${num.slice(0, 5)} ${num.slice(5)}` : "";

  /* ---------------- UI ---------------- */
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        {/* Back */}
        <Pressable onPress={() => router.back()} style={styles.backButton}>
          <ArrowLeft size={24} color="#1F2937" />
        </Pressable>

        <Text style={styles.title}>Verify OTP</Text>
        <Text style={styles.subtitle}>
          We've sent a 6-digit code to {formatMobileNumber(mobileNumber)}
        </Text>

        {/* OTP BOXES */}
        <View style={styles.otpContainer}>
          {otp.map((digit, index) => (
            <TextInput
              key={index}
              style={styles.otpInput}
              value={digit}
              onChangeText={(v) => handleOTPChange(v, index)}
              keyboardType="number-pad"
              maxLength={1}
              textAlign="center"
            />
          ))}
        </View>

        {/* RESEND */}
        <View style={styles.resendContainer}>
          {!canResend ? (
            <Text style={styles.resendText}>
              Resend code in {timeLeft}s
            </Text>
          ) : (
            <Pressable onPress={handleResendOTP}>
              <Text style={styles.resendLink}>Resend OTP</Text>
            </Pressable>
          )}
        </View>

        <Text style={styles.footerText}>
          Having trouble? Contact support at help@medvault.app
        </Text>
      </View>
    </View>
  );
}

/* ---------------- STYLES ---------------- */
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#FFFFFF",
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: "center",
  },
  backButton: {
    marginBottom: 20,
    width: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: "#1F2937",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: "#6B7280",
    marginBottom: 32,
  },
  otpContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 32,
  },
  otpInput: {
    width: 45,
    height: 55,
    borderWidth: 2,
    borderColor: "#D1D5DB",
    borderRadius: 12,
    fontSize: 20,
    fontWeight: "600",
    backgroundColor: "#F9FAFB",
  },
  resendContainer: {
    alignItems: "center",
    marginBottom: 32,
  },
  resendText: {
    color: "#6B7280",
  },
  resendLink: {
    color: "#2563EB",
    fontWeight: "600",
  },
  footerText: {
    textAlign: "center",
    fontSize: 12,
    color: "#9CA3AF",
  },
});

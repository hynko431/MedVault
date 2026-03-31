import AsyncStorage from "@react-native-async-storage/async-storage";
import { apiRequest } from "./api";

export const sendOtp = (mobile: string) =>
    apiRequest("/api/auth/mobile/send-otp", "POST", { mobile });

export const verifyOtp = async (mobile: string, otp: string) => {
    const data = await apiRequest(
        "/api/auth/mobile/verify-otp",
        "POST",
        { mobile, otp }
    );

    await AsyncStorage.setItem("token", data.token);
    await AsyncStorage.setItem("isLoggedIn", "true");

    return data;
};

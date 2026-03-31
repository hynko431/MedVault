import { Image, StyleSheet, Text } from "react-native";

/**
 * IMPORTANT:
 * logo.png is here:
 * app/assets/logo.png
 * This file is here:
 * src/components/UIComponents.js
 * So we go up twice, then into app/assets
 */
import logoSource from "../../app/assets/logo.png";

/* ---------- AppLogo ---------- */
export function AppLogo() {
    return (
        <Image
            source={logoSource}
            style={styles.logo}
            resizeMode="contain"
        />
    );
}

/* ---------- AppTitle ---------- */
export function AppTitle() {
    return <Text style={styles.title}>MedVault</Text>;
}

/* ---------- Tagline ---------- */
export function Tagline() {
    return <Text style={styles.tagline}>Your family health, secured</Text>;
}

/* ---------- LoadingDots ---------- */
export function LoadingDots() {
    return <Text style={styles.loading}>Loading...</Text>;
}

/* ---------- Styles ---------- */
const styles = StyleSheet.create({
    logo: {
        width: 120,
        height: 120,
        marginBottom: 20,
    },
    title: {
        fontSize: 32,
        fontWeight: "700",
        color: "#FFFFFF",
        marginBottom: 8,
    },
    tagline: {
        fontSize: 14,
        color: "#E5E7EB",
        marginBottom: 20,
    },
    loading: {
        fontSize: 12,
        color: "#E5E7EB",
    },
});

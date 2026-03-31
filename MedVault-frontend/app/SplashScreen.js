import { LinearGradient } from "expo-linear-gradient";
import { StyleSheet, View } from "react-native";

import {
  AppLogo,
  AppTitle,
  LoadingDots,
  Tagline,
} from "../src/components/UIComponents";

export default function SplashScreen() {
  return (
    <LinearGradient
      colors={["#2563EB", "#1D4ED8", "#1E3A8A"]}
      start={{ x: 0.5, y: 0 }}
      end={{ x: 0.5, y: 1 }}
      style={styles.container}
    >
      <View style={styles.center}>
        <AppLogo />
        <AppTitle />
        <Tagline />
        <LoadingDots />
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  center: {
    alignItems: "center",
  },
});

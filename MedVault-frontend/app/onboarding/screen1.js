import { Pressable, StyleSheet, Text, View } from 'react-native';

export default function OnboardingScreen1({ onNext }) {
  return (
    <View style={styles.container}>
      <View style={styles.center}>
        <Text style={styles.title}>
          Store all family prescriptions digitally
        </Text>

        {/* Placeholder if image doesn't exist */}
        <View style={styles.imagePlaceholder}>
          <Text style={styles.placeholderText}>📋</Text>
        </View>
      </View>

      <View>
        <Pressable style={styles.primaryBtn} onPress={onNext}>
          <Text style={styles.btnText}>Get Started</Text>
        </Pressable>
        <Progress active={0} />
      </View>
    </View>
  );
}

function Progress({ active }) {
  return (
    <View style={styles.progress}>
      {[0, 1, 2].map(i => (
        <View
          key={i}
          style={[
            styles.bar,
            i === active && styles.activeBar,
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    justifyContent: 'space-between',
    backgroundColor: '#FFFFFF',
  },
  center: {
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  title: {
    fontSize: 26,
    textAlign: 'center',
    marginBottom: 24,
    fontWeight: '600',
    color: '#000',
  },
  imagePlaceholder: {
    width: 260,
    height: 260,
    backgroundColor: '#F3F4F6',
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  placeholderText: {
    fontSize: 80,
  },
  primaryBtn: {
    backgroundColor: '#2563EB',
    paddingVertical: 16,
    borderRadius: 30,
  },
  btnText: {
    color: 'white',
    fontSize: 16,
    textAlign: 'center',
    fontWeight: '600',
  },
  progress: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 16,
  },
  bar: {
    width: 30,
    height: 4,
    backgroundColor: '#D1D5DB',
    borderRadius: 2,
    marginHorizontal: 4,
  },
  activeBar: {
    backgroundColor: '#2563EB',
  },
});

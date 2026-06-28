import React, { Component } from 'react';
import ReactDOM from 'react-dom/client';
import { Text, View, StyleSheet, TouchableOpacity, Dimensions } from 'react-native-web';

const deviceHeight = Dimensions.get('window').height;
const deviceWidth = Dimensions.get('window').width;

export default class App extends Component {
  render() {
    return (
      <View style={styles.page}>
        <View style={styles.navbar}>
          <View style={styles.logoContainer}>
            <Text style={styles.logoText}>TANDEM</Text>
          </View>

          <View style={styles.navActions}>
            <TouchableOpacity style={styles.navButton}>
              <Text style={styles.navButtonText}>Home</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.navButton}>
              <Text style={styles.navButtonText}>About</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.navButton}>
              <Text style={styles.navButtonText}>Contact</Text>
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.content}>
          <Text style={styles.title}>Welcome to Tandem</Text>
          <Text style={styles.subtitle}>Tandem is so cool</Text>
        </View>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  page: {
    minHeight: deviceHeight,
    width: deviceWidth,
    backgroundColor: '#f7f7f7',
    margin: 0,
    padding: 0,
  },
  navbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#ffffff',
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
    width: deviceWidth,
  },
  logoContainer: {
    flex: 1,
    alignItems: 'flex-start',
  },
  logoText: {
    fontSize: 24,
    fontWeight: '700',
    color: '#111827',
    letterSpacing: 1.2,
  },
  navActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  navButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 6,
    marginLeft: 8,
  },
  navButtonText: {
    fontSize: 15,
    color: '#4b5563',
    fontWeight: '600',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 28,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

import React, { Component } from 'react';
import ReactDOM from 'react-dom/client';
import { ScrollView, View, Text, StyleSheet } from 'react-native-web';

export default class App extends Component {
  render() {
    return (
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.card}>
          <Text style={styles.paragraph}>Welcome to Tandem</Text>
        </View>
      </ScrollView>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 20,
    backgroundColor: '#ecf0f1',
    flexDirection: 'column',
    minHeight: '100vh',
  },
  card: {
    width: '100%',
    maxWidth: 600,
    padding: 24,
    backgroundColor: '#ffffff',
    borderRadius: 12,
    alignItems: 'center',
  },
  paragraph: {
    margin: 24,
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    color: '#34495e',
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
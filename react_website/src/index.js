import React, { Component } from 'react';
import ReactDOM from 'react-dom/client';
import { Text, View, StyleSheet, TouchableHighlight, Dimensions, ScrollView, Image } from 'react-native-web';

const deviceHeight = Dimensions.get('window').height;
const deviceWidth = Dimensions.get('window').width;

export default class App extends Component {
  render() {
    return (
      <View style={styles.container}>
        <View style={styles.topBar}>
          <View> </View>
          <View style={styles.logoBox}>
            <Text style={styles.logo}>TANDEM</Text>
          </View>
          <View style={styles.navLinks}>
            <TouchableHighlight
              style={styles.touchableButton}
              onPress={() => window.alert('Alert Message!')}
            >
              <Text style={styles.navButton}>Press me!</Text>
            </TouchableHighlight>
          </View>
        </View>


        <View style={styles.body}> 
          <View style={styles.nav}>
          </View>
          <ScrollView contentContainerStyle={styles.scrollContainer}>
            <View style={styles.card}>
              <Text style={styles.paragraph}>Welcome to Tandem!</Text>
            </View>
          </ScrollView>
        </View>


      </View>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E6E6E6',
    flexDirection: 'column',
    height: deviceHeight,
  },
  scrollContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 24,
    width: deviceWidth,
  },
  nav: {
    backgroundColor: "yellow",
    height: 6/7*deviceHeight,
    width: 2/7*deviceWidth,
    flexDirection: "column",
  },
  body: {
    flexDirection: "row",
    backgroundColor: "red",
    height: 6/7*deviceHeight,
  },
  paragraph: {
    margin: 24,
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    color: '#4d2e00',
  },
  topBar: {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#dba400',
    width: deviceWidth,
    height: deviceHeight / 7,
    flexDirection: 'row',
  },
  logoBox: {
    width: deviceWidth / 2.5,
    alignItems: 'flex-start',
    paddingLeft: 20,
  },
  navLinks: {
    width: deviceWidth / 2,
    alignItems: 'flex-end',
    paddingRight: 20,
  },
  logo: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  touchableButton: {
    padding: 10,
    backgroundColor: '#974B00',
    borderRadius: 8,
  },
  navButton: {
    fontSize: 18,
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
  card: {
    width: deviceWidth * 0.9 * 5/7,
    marginTop: 20,
    padding: 24,
    marginLeft: 0,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    alignItems: 'center',
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

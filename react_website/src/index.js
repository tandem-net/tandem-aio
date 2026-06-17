import React, { Component } from 'react';
import ReactDOM from 'react-dom/client';
import {Text, View, StyleSheet, Image, TextInput, ImageBackground, TouchableHighlight, Alert, Dimensions, ScrollView } from 'react-native-web';

let deviceHeight = Dimensions.get('window').height;
let deviceWidth = Dimensions.get('window').width;

export default class App extends Component {
  render() {
    // add all website content inside scrollview so it's not just a static page.
    return (
      <View contentContainerStyle={styles.container}>
        <View style={styles.topBar}>
          {/* add top bar content here, such as logo and navigation links */}

            <View style={styles.logoBox}>
              <Text style={styles.logo}>TANDEM</Text>
            </View>
            
            <View style={styles.navLinks}>
              <View>
                <TouchableHighlight
                      style={styles.touchableButton}
                      onPress={() => {
                          alert('Alert Message!');
                      }}
                  >
                      <Text style={styles.navButton}>
                          Press me!
                      </Text>
                  </TouchableHighlight>
              </View>
            </View>
        </View>
      <ScrollView>
        <View style={styles.card}>
          <Text style={styles.paragraph}>Welcome to Tandem!</Text>
        </View>
        </ScrollView>
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
  paragraph: {
    margin: 24,
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    color: '#34495e',
  },
  topBar: {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#001F3D',
    width: deviceWidth,
    height: deviceHeight/7,
    flexDirection: 'row',
  },
  logoBox: {
    width: deviceWidth/2,
    alignItems: 'flex-start',
    paddingLeft: 20,
  },
  navLinks: {
    width: deviceWidth/2,
    alignItems: 'flex-end',
    paddingRight: 20,
  },
  logo: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  navButton: {
    fontSize: 18,
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
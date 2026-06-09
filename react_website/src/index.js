import React, { Component } from 'react';
import ReactDOM from 'react-dom/client';
import {Text, View, StyleSheet, Image, TextInput, ImageBackground, TouchableHighlight, Alert, Dimensions, ScrollView } from 'react-native-web';

let deviceHeight = Dimensions.get('window').height;
let deviceWidth = Dimensions.get('window').width;

export default class App extends Component {
  render() {
    return ( // add all website content inside scrollview so it's not just a static page.
/*
 _____               _                
|_   _|_ _ _ __   __| | ___ _ __ ___  
  | |/ _` | '_ \ / _` |/ _ \ '_ ` _ \ 
  | | (_| | | | | (_| |  __/ | | | | |
  |_|\__,_|_| |_|\__,_|\___|_| |_| |_|
*/

      <View contentContainerStyle={styles.container}>
        <View style={styles.topBar}>
          {/* add top bar content here, such as logo and navigation links */}
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
    backgroundColor: '#ecf0f1',
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
    justifyContent: 'flex-start',
    alignItems: 'center',
    backgroundColor: '#65d6d4',
    width: deviceWidth,
    height: deviceHeight/7
  }
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
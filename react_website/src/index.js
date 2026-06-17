import React, { Component } from 'react';
import ReactDOM from 'react-dom/client';
import {Text, View, StyleSheet, Image, TextInput, ImageBackground, TouchableHighlight, Alert, Dimensions, ScrollView } from 'react-native-web';

let deviceHeight = Dimensions.get('window').height;
let deviceWidth = Dimensions.get('window').width;

export default class App extends Component {
  render() {
<<<<<<< HEAD
    // add all website content inside scrollview so it's not just a static page.
    return (
=======
    return ( // add all website content inside scrollview so it's not just a static page.
/*
 _____               _                
|_   _|_ _ _ __   __| | ___ _ __ ___   
  | |/ _` | '_ \ / _` |/ _ \ '_ ` _ \  
  | | (_| | | | | (_| |  __/ | | | | |  
  |_|\__,_|_| |_|\__,_|\___|_| |_| |_| 
*/

>>>>>>> c3b84a2651a6c8a7b97ab7d0ca28394e6cc0fd79
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
    color: '#4d2e00',
  },
  topBar: {
    justifyContent: 'center',
    alignItems: 'center',
<<<<<<< HEAD
    backgroundColor: '#001F3D',
=======
    backgroundColor: '#dba400',
>>>>>>> c3b84a2651a6c8a7b97ab7d0ca28394e6cc0fd79
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
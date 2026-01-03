#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>

#define SERVICE_UUID "06d527b7-9a06-473b-ae8b-4794bae3fa04"
#define CHARACTERISTIC_UUID "8acc4aaf-26b1-44a9-8b83-2d94ce03f34a"

// Initialize variables
int buttons[4] = {18,19,14,3};
volatile bool changeMode = false;
volatile unsigned long prev_time = 0;
volatile unsigned long wait_time = 0;
bool sleepAnnounced = false;
bool connected = false;
BLECharacteristic *pCharacteristic;  

// Used for connection and disconnection
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    connected = true;
    Serial.println("Client connected");
  }

  void onDisconnect(BLEServer* pServer) {
    connected = false;
    Serial.println("Client disconnected");
    // Restart advertising so clients can reconnect
    BLEDevice::startAdvertising();  
  }
};

void setup() 
{
  Serial.begin(115200);

  // Standard setup for BLE taken from the example
  // Used to setup BLE
  BLEDevice::init("Long name works now");
  BLEServer *pServer = BLEDevice::createServer();
  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(CHARACTERISTIC_UUID, 
  BLECharacteristic::PROPERTY_NOTIFY | BLECharacteristic::PROPERTY_READ);

  pCharacteristic->setValue("Hello World");
  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);  // functions that help with iPhone connections issue
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  Serial.println("Characteristic defined! Now you can read it in your phone!");

  pServer->setCallbacks(new MyServerCallbacks());
  // Setup buttons
  for(int i=0;i<4;i++){
    pinMode(buttons[i], INPUT_PULLUP);
  } 
}

void loop() 
{
  // Enter sleep mode when keyboard is inactive
  if(connected){
    if((digitalRead(18) == HIGH) &&
    (digitalRead(19) == HIGH) &&
    (digitalRead(14) == HIGH) &&
    (changeMode == false) && (millis() - wait_time > 3000)){
      if(!sleepAnnounced){ 
        Serial.println("Enter sleep");
        sleepAnnounced = true;
      }
    } else{
      sleepAnnounced = false;
    } 
      // Runs the keyboard code (active phase)
      computerModeSelected();
  }
}

// Loops through all the buttons and checks if any are pressed.
// When they are pressed, it sends a BLE message saying which button was pressed
void computerModeSelected(){
  for(int i = 0; i < 4 ; i++){
    // Check is the button is pressed
    if(digitalRead(buttons[i]) == LOW){
      // Wait for which button will be pressed
      switch(buttons[i]){
        case 3:
          pCharacteristic->setValue("BTN:1");
          pCharacteristic->notify();
          // Serial.println("BTN:1");  //DEBUG
          delay(200);
          wait_time = millis();
          break;

        case 18: 
          pCharacteristic->setValue("BTN:2");
          pCharacteristic->notify();
          // Serial.println("BTN:2");  //DEBUG
          delay(200);
          wait_time = millis();
          break;
        
        case 19:
          pCharacteristic->setValue("BTN:3");
          pCharacteristic->notify();
          // Serial.println("BTN:3");  //DEBUG
          delay(200);
          wait_time = millis();
          break;
        
        case 14:
          pCharacteristic->setValue("BTN:4");
          pCharacteristic->notify();
          // Serial.println("BTN:4");  //DEBUG
          delay(200);
          wait_time = millis();
          break;        
        
        default:
          Serial.println("No button was found");
          wait_time = millis();
          break;        
      }
    }
  }
}

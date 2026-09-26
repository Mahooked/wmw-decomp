# Levels format (Levels/*.xml)

Parsed 636 files; 12 distinct element paths.

'instances' counts how many times that element occurs across all
files; 'children' is the breakdown of what it contains.

element path                                         instances  attributes (value shape)
----------------------------------------------------------------------------------------------------
/Objects/Object/Properties/Property                      81195  name:empty/string  value:asset path/empty/float/int/string/two floats
/Objects/Object/Properties                               27043  
                                                                children: Property x81195
/Objects/Object                                          27043  name:int/string
                                                                children: AbsoluteLocation x27043, Properties x27043
/Objects/Object/AbsoluteLocation                         27043  value:two floats
/Objects/Room/AbsoluteLocation                             636  value:two floats
/Objects/Room                                              636  
                                                                children: AbsoluteLocation x636
/Objects                                                   636  
                                                                children: Object x27043, Room x636, Properties x222, Region x1, Lighting x1
/Objects/Properties/Property                               335  name:string  value:float/int
/Objects/Properties                                        222  
                                                                children: Property x335
/Objects/Lighting                                            1  filename:asset path
/Objects/Region                                              1  brCell:number list  tlCell:number list
                                                                children: Properties x1
/Objects/Region/Properties                                   1  
